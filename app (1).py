import os
import logging
import uuid
import tempfile
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
import pandas as pd
import io
from werkzeug.utils import secure_filename
from calculadora import calcular_horas_excel
from horarios_flexibles import calcular_horas_excel_flexibles
from pdf_protector import procesar_pdf_batch, proteger_pdf
from boletas_pago import procesar_boletas_excel, numero_a_letras
from certificados_utilidades import procesar_certificados_batch

# Configurar logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "clave_secreta_calculadora_horas")

# Configurar las extensiones permitidas para archivos Excel y PDF
EXTENSIONES_EXCEL_PERMITIDAS = {'xlsx', 'xls'}
EXTENSIONES_PDF_PERMITIDAS = {'pdf'}

# Almacenamiento temporal para PDFs procesados
PDF_PROCESADOS = {}

def extension_permitida(filename, extensiones):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in extensiones

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Verificar si se recibió el archivo
        if 'archivo' not in request.files:
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        archivo = request.files['archivo']
        
        # Validar que se haya seleccionado un archivo
        if archivo.filename == '':
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        # Validar la extensión del archivo
        if not extension_permitida(archivo.filename, EXTENSIONES_EXCEL_PERMITIDAS):
            flash('Por favor, sube un archivo Excel válido (.xlsx o .xls)', 'danger')
            return redirect(request.url)
        
        # Procesar el archivo
        try:
            nombre_hoja = request.form.get('nombre_hoja', 'Horas')
            
            # Obtener las columnas personalizadas si se especificaron
            columna_inicio = request.form.get('columna_inicio', 'Hora Inicio')
            columna_fin = request.form.get('columna_fin', 'Hora Fin')
            columna_refrigerio_inicio = request.form.get('columna_refrigerio_inicio', 'Hora Refrigerio Inicio')
            columna_refrigerio_fin = request.form.get('columna_refrigerio_fin', 'Hora Refrigerio Fin')
            
            # Verificar si se seleccionó el modo horarios flexibles
            usar_horarios_flexibles = 'usar_horarios_flexibles' in request.form
            
            # Leer el archivo
            bytes_data = io.BytesIO()
            archivo.save(bytes_data)
            bytes_data.seek(0)
            
            # Procesar el archivo con la función de cálculo según el modo seleccionado
            if usar_horarios_flexibles:
                app.logger.info("Usando cálculo de horarios flexibles")
                df_resultado, mensaje = calcular_horas_excel_flexibles(
                    bytes_data, 
                    nombre_hoja=nombre_hoja,
                    col_inicio=columna_inicio,
                    col_fin=columna_fin,
                    col_refrigerio_inicio=columna_refrigerio_inicio,
                    col_refrigerio_fin=columna_refrigerio_fin
                )
            else:
                app.logger.info("Usando cálculo de horarios normal")
                df_resultado, mensaje = calcular_horas_excel(
                    bytes_data, 
                    nombre_hoja=nombre_hoja,
                    col_inicio=columna_inicio,
                    col_fin=columna_fin,
                    col_refrigerio_inicio=columna_refrigerio_inicio,
                    col_refrigerio_fin=columna_refrigerio_fin
                )
            
            if df_resultado is None:
                flash(mensaje, 'danger')
                return redirect(request.url)
            
            # Guardar el DataFrame en un buffer de bytes para descargarlo
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_resultado.to_excel(writer, index=False, sheet_name='Reporte')
            output.seek(0)
            
            # Guardar el resultado en la sesión para mostrarlo en la página de resultados
            return send_file(
                output,
                as_attachment=True,
                download_name='reporte_horas_calculadas.xlsx',
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
        except Exception as e:
            app.logger.error(f"Error al procesar el archivo: {str(e)}")
            flash(f'Error al procesar el archivo: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('index.html')

@app.route('/protector-pdf', methods=['GET', 'POST'])
def proteger_pdf():
    resultados = {}
    
    if request.method == 'POST':
        # Verificar si se recibieron archivos
        if 'archivos' not in request.files:
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        archivos = request.files.getlist('archivos')
        
        # Validar que se hayan seleccionado archivos
        if not archivos or archivos[0].filename == '':
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        # Procesar cada archivo
        archivos_para_procesar = []
        
        for archivo in archivos:
            # Validar la extensión del archivo
            if not extension_permitida(archivo.filename, EXTENSIONES_PDF_PERMITIDAS):
                flash(f'El archivo {archivo.filename} no es un PDF válido', 'warning')
                continue
            
            # Guardar temporalmente el archivo
            bytes_data = io.BytesIO()
            archivo.save(bytes_data)
            archivos_para_procesar.append((archivo.filename, bytes_data))
        
        if not archivos_para_procesar:
            flash('No se procesó ningún archivo. Verifica que sean PDFs válidos.', 'danger')
            return redirect(request.url)
        
        # Obtener configuración
        usar_nombre_archivo = 'usar_nombre_archivo' in request.form
        contraseña_manual = request.form.get('contraseña', '')
        
        # Proteger PDFs
        resultados_procesamiento = procesar_pdf_batch(
            archivos_para_procesar,
            usar_nombre_archivo=usar_nombre_archivo,
            contraseña_manual=contraseña_manual if not usar_nombre_archivo and contraseña_manual else None
        )
        
        # Preparar resultados para la vista
        for nombre, (pdf_data, mensaje_o_contraseña) in resultados_procesamiento.items():
            if pdf_data is not None:
                # Éxito - guardar en memoria y generar ID único
                file_id = str(uuid.uuid4())
                PDF_PROCESADOS[file_id] = pdf_data
                resultados[nombre] = {
                    'exito': True,
                    'contraseña': mensaje_o_contraseña,
                    'id': file_id
                }
            else:
                # Error
                resultados[nombre] = {
                    'exito': False,
                    'mensaje': mensaje_o_contraseña,
                    'contraseña': None
                }
        
        if all(not info['exito'] for info in resultados.values()):
            flash('No se pudo proteger ningún archivo. Verifica el formato de los nombres.', 'danger')
    
    return render_template('pdf_protector.html', resultados=resultados)

@app.route('/descargar-pdf/<filename>/<nombre_original>')
def descargar_pdf(filename, nombre_original):
    # Verificar si el archivo existe en el almacenamiento temporal
    if filename not in PDF_PROCESADOS:
        flash('El archivo solicitado no está disponible o ha expirado.', 'danger')
        return redirect(url_for('proteger_pdf'))
    
    # Obtener los datos del PDF
    data = PDF_PROCESADOS[filename]
    
    # Verificar si es un diccionario con pdf_data, un BytesIO directamente o si son datos para generar boleta
    if isinstance(data, dict) and 'pdf_data' in data:
        # Es un certificado en formato anidado
        pdf_data = data['pdf_data']
        try:
            pdf_data.tell()  # Comprueba si el archivo está cerrado
        except ValueError:
            # Si el archivo está cerrado, usar una copia del contenido
            app.logger.warning(f"El archivo {filename} (pdf_data) estaba cerrado, creando una nueva copia.")
            contenido = pdf_data.getvalue() if hasattr(pdf_data, 'getvalue') else None
            if contenido:
                pdf_data = io.BytesIO(contenido)
            else:
                flash('Error al procesar el archivo PDF.', 'danger')
                return redirect(url_for('index'))
        pdf_data.seek(0)
    elif isinstance(data, io.BytesIO):
        # Es un PDF ya generado (protegido)
        # Verificar si el archivo no está cerrado
        try:
            data.tell()  # Comprueba si el archivo está cerrado
        except ValueError:
            # Si el archivo está cerrado, usar una copia del contenido
            app.logger.warning(f"El archivo {filename} estaba cerrado, creando una nueva copia.")
            contenido = data.getvalue() if hasattr(data, 'getvalue') else None
            if contenido:
                data = io.BytesIO(contenido)
            else:
                flash('Error al procesar el archivo PDF.', 'danger')
                return redirect(url_for('index'))
        
        pdf_data = data
        pdf_data.seek(0)
    elif isinstance(data, dict) and 'datos' in data:
        # Son datos para generar una boleta de pago
        try:
            # Generar la boleta de pago con diseño mejorado
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.units import inch
            import textwrap
            import datetime
            from boletas_pago import numero_a_letras
            
            # Crear un buffer para el PDF
            pdf_buffer = io.BytesIO()
            
            # Crear el canvas
            c = canvas.Canvas(pdf_buffer, pagesize=letter)
            width, height = letter
            
            # Obtener los datos
            datos_empleado = data['datos']['datos_personales']
            ingresos = data['datos']['ingresos']
            descuentos = data['datos']['descuentos']
            aportes = data['datos']['aportes']
            
            # Convertir periodo a formato conveniente
            periodo_str = str(datos_empleado.get('periodo', ''))
            periodo_partes = periodo_str.split('/')
            mes = ""
            año = ""
            
            if len(periodo_partes) >= 2:
                try:
                    mes_num = int(periodo_partes[0])
                    meses = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", 
                             "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]
                    if 1 <= mes_num <= 12:
                        mes = meses[mes_num - 1]
                    año = periodo_partes[1]
                except (ValueError, IndexError):
                    mes = periodo_partes[0]
                    año = periodo_partes[1]
            
            # Encabezado de la boleta
            c.setFont("Helvetica-Bold", 12)
            c.drawRightString(width - 50, height - 40, f"BOLETA DE PAGO {mes} {año}")
            c.drawRightString(width - 50, height - 55, "D.S. N°017-2001-TR DEL 07-06-01")
            
            # Información de la empresa
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, height - 80, "Razon Social:")
            c.drawString(50, height - 95, "Domicilio   :")
            c.drawString(50, height - 110, "R.U.C.      :")
            
            c.setFont("Helvetica", 10)
            c.drawString(130, height - 80, "EMPRESA S.A.C")
            c.drawString(130, height - 95, "AV. PRINCIPAL 123 - CIUDAD")
            c.drawString(130, height - 110, "20XXXXXXXXX")
            
            # Línea separadora
            c.line(50, height - 125, width - 50, height - 125)
            
            # Datos del trabajador
            c.setFont("Helvetica-Bold", 11)
            c.drawString(50, height - 145, "DATOS DEL TRABAJADOR")
            
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, height - 165, "Nombre :")
            c.drawString(50, height - 180, "Cargo :")
            
            c.setFont("Helvetica", 10)
            c.drawString(130, height - 165, f"{datos_empleado.get('nombre', '')}")
            c.drawString(130, height - 180, f"{datos_empleado.get('cargo', '')}")
            
            # Segunda fila de datos
            c.setFont("Helvetica-Bold", 9)
            y_pos = height - 200
            c.drawString(50, y_pos, "Código :")
            c.drawString(120, y_pos, f"{datos_empleado.get('dni', '')}")
            c.drawString(180, y_pos, "T.Pensión :")
            c.drawString(250, y_pos, "AFP Integra")
            c.drawString(350, y_pos, "F.Ingr.:")
            fecha_ingreso = str(datos_empleado.get('fecha_ingreso', ''))
            c.drawString(400, y_pos, f"{fecha_ingreso}")
            c.drawString(480, y_pos, "D.Trab :")
            c.drawString(525, y_pos, "30")
            
            # Línea separadora
            y_pos -= 20
            c.line(50, y_pos, width - 50, y_pos)
            
            # Encabezados de secciones
            y_pos -= 15
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y_pos, "REMUNERACIONES")
            c.drawString(300, y_pos, "DESCUENTOS TRABAJADOR")
            c.drawString(480, y_pos, "APORTES EMPLEADOR")
            
            # Línea separadora
            y_pos -= 10
            c.line(50, y_pos, width - 50, y_pos)
            
            # Contenido de secciones
            y_pos -= 25
            c.setFont("Helvetica", 9)
            
            # Calcular altura máxima para las columnas
            max_items = max(len(ingresos), len(descuentos), len(aportes))
            item_height = 15
            
            # Ingresos
            ingreso_y = y_pos
            for ingreso in ingresos:
                c.drawString(50, ingreso_y, f"{ingreso['concepto']}")
                c.drawRightString(250, ingreso_y, f"S/ {ingreso['monto']:.2f}")
                ingreso_y -= item_height
            
            # Descuentos
            descuento_y = y_pos
            for descuento in descuentos:
                c.drawString(300, descuento_y, f"{descuento['concepto']}")
                c.drawRightString(450, descuento_y, f"S/ {descuento['monto']:.2f}")
                descuento_y -= item_height
            
            # Aportes
            aporte_y = y_pos
            for aporte in aportes:
                c.drawString(480, aporte_y, f"{aporte['concepto']}")
                c.drawRightString(550, aporte_y, f"S/ {aporte['monto']:.2f}")
                aporte_y -= item_height
            
            # Calcular espacio usado
            min_y = min(ingreso_y, descuento_y, aporte_y)
            
            # Línea separadora
            min_y -= 10
            c.line(50, min_y, width - 50, min_y)
            
            # Totales
            min_y -= 25
            c.setFont("Helvetica-Bold", 9)
            c.drawString(50, min_y, "TOTAL HABER")
            c.drawRightString(250, min_y, f"S/ {datos_empleado.get('total_remuneracion', 0):.2f}")
            
            c.drawString(300, min_y, "TOTAL DESCUENTOS")
            c.drawRightString(450, min_y, f"S/ {datos_empleado.get('total_descuentos', 0):.2f}")
            
            c.drawString(480, min_y, "TOTAL APORTES")
            c.drawRightString(550, min_y, f"S/ {datos_empleado.get('total_aportes', 0):.2f}")
            
            # Línea separadora
            min_y -= 10
            c.line(50, min_y, width - 50, min_y)
            
            # Neto a pagar
            min_y -= 20
            c.drawString(50, min_y, "NETO A PAGAR EN:")
            
            # Asegurarse de que neto_pagar sea un número
            neto_pagar = datos_empleado.get('neto_pagar', 0)
            if not isinstance(neto_pagar, (int, float)):
                try:
                    neto_pagar = float(neto_pagar)
                except (ValueError, TypeError):
                    neto_pagar = 0.0
            
            c.drawRightString(250, min_y, f"S/ {neto_pagar:.2f}")
            
            # Fecha de pago
            min_y -= 20
            fecha_actual = datetime.datetime.now()
            
            # Intentar obtener año y mes del periodo
            año_pago = año if año else str(fecha_actual.year)
            try:
                mes_pago = int(mes_num) if 'mes_num' in locals() and mes_num is not None and 1 <= int(mes_num) <= 12 else fecha_actual.month
            except:
                mes_pago = fecha_actual.month
            
            # Crear fecha de pago (último día del mes)
            try:
                # Calcular el siguiente mes y año
                if mes_pago == 12:
                    siguiente_mes = 1
                    siguiente_año = int(año_pago) + 1
                else:
                    siguiente_mes = mes_pago + 1
                    siguiente_año = int(año_pago)
                
                # El último día del mes es un día antes del primer día del siguiente mes
                ultimo_dia = (datetime.datetime(siguiente_año, siguiente_mes, 1) - datetime.timedelta(days=1)).day
                fecha_pago = f"{ultimo_dia:02d}/{mes_pago:02d}/{año_pago}"
            except (ValueError, TypeError):
                fecha_pago = f"{fecha_actual.strftime('%d/%m/%Y')}"
            
            c.drawString(50, min_y, "Fecha de Pago :")
            c.drawString(130, min_y, fecha_pago)
            
            # Firmas
            min_y -= 60
            c.line(100, min_y, 250, min_y)
            c.line(350, min_y, 500, min_y)
            
            min_y -= 10
            c.drawCentredString(175, min_y, "Empleador")
            c.drawCentredString(425, min_y, "Trabajador")
            
            # Finalizar el PDF
            c.showPage()
            c.save()
            
            pdf_buffer.seek(0)
            pdf_data = pdf_buffer
            
        except Exception as e:
            app.logger.error(f"Error al generar la boleta de pago: {str(e)}")
            flash(f'Error al generar la boleta de pago: {str(e)}', 'danger')
            return redirect(url_for('boletas_pago'))
    
    # Eliminar el archivo del almacenamiento después de descargarlo
    # (comentado para poder descargar múltiples veces durante la misma sesión)
    # del PDF_PROCESADOS[filename]
    
    # Determinar el nombre de archivo para la descarga
    # Inicializar variable de nombre de descarga con valor predeterminado
    download_name = nombre_original if nombre_original.lower().endswith('.pdf') else f"{nombre_original}.pdf"
    
    if isinstance(data, io.BytesIO):
        # Es un certificado o PDF protegido (dato directo)
        if filename in PDF_PROCESADOS:
            if isinstance(PDF_PROCESADOS[filename], dict) and 'nombre_archivo' in PDF_PROCESADOS[filename]:
                # Es una boleta o certificado con nombre específico
                download_name = PDF_PROCESADOS[filename]['nombre_archivo']
            elif 'pdf_data' in PDF_PROCESADOS[filename]:
                # Es un certificado con estructura anidada
                download_name = PDF_PROCESADOS[filename].get('nombre_archivo', download_name)
    else:
        # Es una boleta, usar el nombre almacenado
        download_name = data.get('nombre_archivo', download_name)
    
    return send_file(
        pdf_data,
        as_attachment=True,
        download_name=download_name,
        mimetype='application/pdf'
    )

@app.route('/boletas-pago', methods=['GET', 'POST'])
def boletas_pago():
    resultados = {}
    
    if request.method == 'POST':
        # Verificar si se recibió el archivo
        if 'archivo' not in request.files:
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        archivo = request.files['archivo']
        
        # Validar que se haya seleccionado un archivo
        if archivo.filename == '':
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        # Validar la extensión del archivo
        if not extension_permitida(archivo.filename, EXTENSIONES_EXCEL_PERMITIDAS):
            flash('Por favor, sube un archivo Excel válido (.xlsx o .xls)', 'danger')
            return redirect(request.url)
        
        # Procesar el archivo
        try:
            # Obtener el nombre de la hoja
            nombre_hoja = request.form.get('nombre_hoja', 'Empleados')
            
            # Leer el archivo
            bytes_data = io.BytesIO()
            archivo.save(bytes_data)
            bytes_data.seek(0)
            
            # Procesar boletas
            empleados, mensaje = procesar_boletas_excel(bytes_data, hoja=nombre_hoja)
            
            if empleados is None:
                flash(mensaje, 'danger')
                return redirect(request.url)
            
            # Generar PDFs (simulado para prueba)
            boletas_generadas = {}
            
            for nombre, datos in empleados.items():
                # Generar un ID único para la boleta
                boleta_id = str(uuid.uuid4())
                
                # Convertir neto a pagar a palabras
                neto_pagar = datos['datos_personales'].get('neto_pagar', 0)
                # Asegurarse de que neto_pagar sea un número
                if not isinstance(neto_pagar, (int, float)):
                    try:
                        neto_pagar = float(neto_pagar)
                    except (ValueError, TypeError):
                        neto_pagar = 0.0
                
                neto_pagar_letras = numero_a_letras(neto_pagar)
                
                # Guardar datos para mostrar en la plantilla de resultados
                boletas_generadas[nombre] = {
                    'id': boleta_id,
                    'dni': datos['datos_personales'].get('dni', ''),
                    'periodo': datos['datos_personales'].get('periodo', ''),
                    'neto_pagar': neto_pagar,
                    'neto_pagar_letras': neto_pagar_letras
                }
                
                # Guardar los datos para generar el PDF cuando se solicite
                periodo_str = str(datos['datos_personales'].get('periodo', '')).replace('/', '_')
                
                PDF_PROCESADOS[boleta_id] = {
                    'datos': datos,
                    'nombre_archivo': f"BOLETA_{datos['datos_personales'].get('dni', '')}_{periodo_str}.pdf"
                }
            
            # Obtener el periodo y asegurarse de que sea un string
            periodo = ''
            if empleados:
                periodo_raw = list(empleados.values())[0]['datos_personales'].get('periodo', '')
                periodo = str(periodo_raw)
            
            return render_template(
                'boletas_resultado.html', 
                boletas=boletas_generadas,
                periodo=periodo
            )
            
        except Exception as e:
            import traceback
            app.logger.error(f"Error al procesar el archivo de boletas: {str(e)}")
            app.logger.error(traceback.format_exc())
            flash(f'Error al procesar el archivo: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('boletas_pago.html')

@app.route('/certificados-utilidades', methods=['GET', 'POST'])
def certificados_utilidades():
    certificados_generados = {}
    
    if request.method == 'POST':
        # Verificar si se recibió el archivo
        if 'archivo' not in request.files:
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        archivo = request.files['archivo']
        
        # Validar que se haya seleccionado un archivo
        if archivo.filename == '':
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        # Validar la extensión del archivo
        if not extension_permitida(archivo.filename, EXTENSIONES_EXCEL_PERMITIDAS):
            flash('Por favor, sube un archivo Excel válido (.xlsx o .xls)', 'danger')
            return redirect(request.url)
        
        # Procesar el archivo
        try:
            nombre_hoja = request.form.get('nombre_hoja', 'Empleados')
            
            # Leer el archivo
            bytes_data = io.BytesIO()
            archivo.save(bytes_data)
            bytes_data.seek(0)
            
            # Procesar el archivo con la función de certificados
            certificados, mensaje = procesar_certificados_batch(bytes_data, hoja=nombre_hoja)
            
            if certificados is None:
                flash(mensaje, 'danger')
                return redirect(request.url)
            
            # Guardar certificados para mostrar en la plantilla
            for nombre_empleado, pdf_data in certificados.items():
                # Generar ID único para acceder al PDF
                certificado_id = str(uuid.uuid4())
                
                # Guardar en memoria con nombre de archivo específico
                PDF_PROCESADOS[certificado_id] = {
                    'pdf_data': pdf_data,
                    'nombre_archivo': f"Certificado_Liquidacion_{nombre_empleado}.pdf"
                }
                
                # Guardar datos para mostrar en la plantilla
                certificados_generados[nombre_empleado] = {
                    'id': certificado_id,
                    'nombre': nombre_empleado.replace('_', ' '),
                    'nombre_archivo': f"Certificado_Liquidacion_{nombre_empleado}.pdf"
                }
            
            # Mostrar resultados
            return render_template(
                'certificados_resultado.html', 
                certificados=certificados_generados,
                mensaje=mensaje
            )
            
        except Exception as e:
            import traceback
            app.logger.error(f"Error al procesar el archivo de certificados: {str(e)}")
            app.logger.error(traceback.format_exc())
            flash(f'Error al procesar el archivo: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('certificados_utilidades.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    flash('Error interno del servidor. Por favor, intenta nuevamente.', 'danger')
    return render_template('index.html'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
