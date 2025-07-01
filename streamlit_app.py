import streamlit as st
import pandas as pd
import io
from datetime import datetime
import base64

# Configuración de la página
st.set_page_config(
    page_title="Calculadora ESSALUD - TAMBO",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal
st.title("🏥 Calculadora de ESSALUD - TAMBO")
st.markdown("---")

# Descripción de la aplicación
st.markdown("""
### Descripción
Esta aplicación procesa archivos Excel para calcular los importes de ESSALUD según las reglas específicas de TAMBO.

**Funcionalidades principales:**
- Cálculo automático de DÍAS PLAME
- Aplicación de fórmulas de ESSALUD según condiciones específicas
- Manejo de fechas de ingreso y cese
- Procesamiento de días de subsidio
- Exportación de resultados en Excel
""")

def calcular_importe(row):
    """
    Función para calcular el importe según las condiciones específicas
    """
    if pd.notna(row['fecha_cese']):  # Si hay fecha de cese
        return row['Importe Bruto'] * 0.09  # Aplica importe * 9% sin importar el valor
    elif row['Días Subsidio'] > 0:
        return 1130 * 0.09  # Si el importe es menor a 1130, aplica la fórmula 1130 * 9%
    elif row['Importe Bruto'] < 1130 and row['Importe Bruto'] > 0:
        return 1130 * 0.09  # Si el importe es menor a 1130, aplica la fórmula 1130 * 9%
    else:
        return row['Importe Bruto'] * 0.09  # Si el importe es mayor o igual a 1130, aplica importe * 9%

def calcular_calculo_dias_plame(row):
    """
    Función para calcular CALCULO DIAS PLAME
    """
    if row['Días Subsidio'] > 0:
        return round((101.70 / row['Dias_Mes']) * row['DIAS PLAME'], 2)
    else:
        return 0

def procesar_archivo_essalud(df_input):
    """
    Procesa el archivo de entrada aplicando todas las fórmulas de ESSALUD
    """
    try:
        # Crear una copia del DataFrame para no modificar el original
        df = df_input.copy()
        
        # Convertir las fechas de ingreso y cese a formato datetime
        df['fecha_ingreso'] = pd.to_datetime(df['fecha_ingreso'], format='%d/%m/%Y', errors='coerce')
        df['fecha_cese'] = pd.to_datetime(df['fecha_cese'], format='%d/%m/%Y', errors='coerce')
        
        # Calcular la columna DIAS PLAME (Días del mes - Días subsidio)
        df['DIAS PLAME'] = df['Dias_Mes'] - df['Días Subsidio']
        
        # Agregar la nueva columna 'Importe_Calculado' con la fórmula
        df['Importe_Calculado'] = df.apply(calcular_importe, axis=1)
        
        # Calcular CALCULO DIAS PLAME para cada fila
        df['CALCULO DIAS PLAME'] = df.apply(calcular_calculo_dias_plame, axis=1)
        
        # Comparar las columnas y registrar el valor mayor en IMPORTE ESSALUD FINAL
        # Asegurar que las columnas existan antes de aplicar max
        columnas_comparar = []
        if 'Importe_Calculado' in df.columns:
            columnas_comparar.append('Importe_Calculado')
        if 'CALCULO DIAS PLAME' in df.columns:
            columnas_comparar.append('CALCULO DIAS PLAME')
        if 'Importe ESSALUD EJB' in df.columns:
            columnas_comparar.append('Importe ESSALUD EJB')
        
        if columnas_comparar:
            df['IMPORTE ESSALUD FINAL'] = df[columnas_comparar].max(axis=1)
        else:
            df['IMPORTE ESSALUD FINAL'] = 0
        
        return df, None
        
    except Exception as e:
        return None, f"Error al procesar el archivo: {str(e)}"

def crear_excel_descarga(df):
    """
    Crea un archivo Excel para descarga
    """
    output = io.BytesIO()
    # Crear el archivo Excel en memoria
    df.to_excel(output, index=False, sheet_name='Resultados ESSALUD', engine='xlsxwriter')
    output.seek(0)
    return output

def get_table_download_link(df, filename="resultados_essalud.xlsx"):
    """
    Genera un enlace de descarga para el DataFrame
    """
    excel_file = crear_excel_descarga(df)
    b64 = base64.b64encode(excel_file.read()).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">📥 Descargar archivo Excel procesado</a>'
    return href

# Sidebar para instrucciones
with st.sidebar:
    st.header("📋 Instrucciones")
    st.markdown("""
    ### Formato requerido del Excel:
    
    **Columnas necesarias:**
    - `fecha_ingreso` (formato: DD/MM/YYYY)
    - `fecha_cese` (formato: DD/MM/YYYY, puede estar vacío)
    - `Importe Bruto` (número)
    - `Días Subsidio` (número)
    - `Dias_Mes` (número)
    - `Importe ESSALUD EJB` (número)
    
    ### Proceso:
    1. Sube tu archivo Excel
    2. Revisa los datos cargados
    3. Procesa los cálculos
    4. Descarga el resultado
    """)
    
    st.markdown("---")
    st.markdown("### 🔧 Configuración")
    mostrar_calculos = st.checkbox("Mostrar detalles de cálculos", value=False)

# Área principal de la aplicación
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📂 Cargar Archivo Excel")
    
    archivo_subido = st.file_uploader(
        "Selecciona tu archivo Excel",
        type=['xlsx', 'xls'],
        help="El archivo debe contener las columnas requeridas según las instrucciones del sidebar"
    )

with col2:
    if archivo_subido is not None:
        st.success("✅ Archivo cargado correctamente")
        st.info(f"**Nombre:** {archivo_subido.name}")
        st.info(f"**Tamaño:** {round(archivo_subido.size/1024, 1)} KB")

# Procesamiento del archivo
if archivo_subido is not None:
    try:
        # Leer el archivo Excel
        df_original = pd.read_excel(archivo_subido)
        
        st.header("📊 Vista Previa de Datos")
        
        # Mostrar información básica del archivo
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de filas", len(df_original))
        with col2:
            st.metric("Total de columnas", len(df_original.columns))
        with col3:
            st.metric("Memoria utilizada", f"{round(df_original.memory_usage(deep=True).sum()/1024, 1)} KB")
        
        # Mostrar las primeras filas
        st.subheader("Primeras 5 filas del archivo:")
        st.dataframe(df_original.head(), use_container_width=True)
        
        # Verificar columnas requeridas
        columnas_requeridas = ['fecha_ingreso', 'fecha_cese', 'Importe Bruto', 'Días Subsidio', 'Dias_Mes', 'Importe ESSALUD EJB']
        columnas_faltantes = [col for col in columnas_requeridas if col not in df_original.columns]
        
        if columnas_faltantes:
            st.error(f"❌ Columnas faltantes: {', '.join(columnas_faltantes)}")
            st.info("Por favor, asegúrate de que tu archivo Excel contenga todas las columnas requeridas.")
        else:
            st.success("✅ Todas las columnas requeridas están presentes")
            
            # Botón para procesar
            if st.button("🚀 Procesar Cálculos de ESSALUD", type="primary"):
                with st.spinner("Procesando cálculos..."):
                    df_procesado, error = procesar_archivo_essalud(df_original)
                    
                    if error:
                        st.error(f"❌ Error durante el procesamiento: {error}")
                    elif df_procesado is not None:
                        st.success("✅ ¡Procesamiento completado exitosamente!")
                        
                        # Mostrar resultados
                        st.header("📈 Resultados del Procesamiento")
                        
                        # Métricas de resultados - verificar que las columnas existan
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            if 'IMPORTE ESSALUD FINAL' in df_procesado.columns:
                                total_importe_final = df_procesado['IMPORTE ESSALUD FINAL'].sum()
                                st.metric("Total ESSALUD Final", f"S/ {total_importe_final:,.2f}")
                            else:
                                st.metric("Total ESSALUD Final", "No disponible")
                        with col2:
                            if 'Días Subsidio' in df_procesado.columns:
                                empleados_con_subsidio = (df_procesado['Días Subsidio'] > 0).sum()
                                st.metric("Empleados con Subsidio", empleados_con_subsidio)
                            else:
                                st.metric("Empleados con Subsidio", "No disponible")
                        with col3:
                            if 'fecha_cese' in df_procesado.columns:
                                empleados_con_cese = df_procesado['fecha_cese'].notna().sum()
                                st.metric("Empleados con Cese", empleados_con_cese)
                            else:
                                st.metric("Empleados con Cese", "No disponible")
                        with col4:
                            if 'DIAS PLAME' in df_procesado.columns:
                                promedio_dias_plame = df_procesado['DIAS PLAME'].mean()
                                st.metric("Promedio Días PLAME", f"{promedio_dias_plame:.1f}")
                            else:
                                st.metric("Promedio Días PLAME", "No disponible")
                        
                        # Mostrar tabla de resultados
                        st.subheader("Tabla de Resultados Completa:")
                        st.dataframe(df_procesado, use_container_width=True)
                        
                        # Mostrar detalles de cálculos si está habilitado
                        if mostrar_calculos:
                            st.subheader("🔍 Detalles de Cálculos")
                            
                            # Crear tabs para diferentes vistas
                            tab1, tab2, tab3 = st.tabs(["Análisis por Subsidio", "Análisis por Cese", "Resumen General"])
                            
                            with tab1:
                                empleados_subsidio = df_procesado[df_procesado['Días Subsidio'] > 0]
                                if len(empleados_subsidio) > 0:
                                    st.write("**Empleados con días de subsidio:**")
                                    st.dataframe(empleados_subsidio[['fecha_ingreso', 'Días Subsidio', 'DIAS PLAME', 'CALCULO DIAS PLAME']], use_container_width=True)
                                else:
                                    st.info("No hay empleados con días de subsidio")
                            
                            with tab2:
                                empleados_cese = df_procesado[df_procesado['fecha_cese'].notna()]
                                if len(empleados_cese) > 0:
                                    st.write("**Empleados con fecha de cese:**")
                                    st.dataframe(empleados_cese[['fecha_ingreso', 'fecha_cese', 'Importe Bruto', 'Importe_Calculado']], use_container_width=True)
                                else:
                                    st.info("No hay empleados con fecha de cese")
                            
                            with tab3:
                                st.write("**Estadísticas generales:**")
                                stats_df = pd.DataFrame({
                                    'Métrica': ['Importe Bruto Promedio', 'Días Subsidio Promedio', 'ESSALUD Final Promedio'],
                                    'Valor': [
                                        f"S/ {df_procesado['Importe Bruto'].mean():.2f}",
                                        f"{df_procesado['Días Subsidio'].mean():.1f}",
                                        f"S/ {df_procesado['IMPORTE ESSALUD FINAL'].mean():.2f}"
                                    ]
                                })
                                st.dataframe(stats_df, use_container_width=True)
                        
                        # Generar enlace de descarga
                        st.header("💾 Descargar Resultados")
                        
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        nombre_archivo = f"essalud_procesado_{timestamp}.xlsx"
                        
                        st.markdown(
                            get_table_download_link(df_procesado, nombre_archivo),
                            unsafe_allow_html=True
                        )
                        
                        st.info("💡 El archivo descargado incluye todas las columnas originales más los nuevos cálculos de ESSALUD")
    
    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {str(e)}")
        st.info("Por favor, verifica que el archivo sea un Excel válido y contenga los datos en el formato correcto.")

else:
    # Mensaje de bienvenida cuando no hay archivo
    st.info("👆 Por favor, carga un archivo Excel para comenzar el procesamiento")
    
    # Mostrar ejemplo de estructura
    st.header("📋 Ejemplo de Estructura de Datos")
    
    ejemplo_data = {
        'fecha_ingreso': ['01/01/2023', '15/02/2023', '30/03/2023'],
        'fecha_cese': ['', '31/12/2023', ''],
        'Importe Bruto': [1200.00, 800.00, 1500.00],
        'Días Subsidio': [0, 5, 0],
        'Dias_Mes': [30, 30, 30],
        'Importe ESSALUD EJB': [108.00, 72.00, 135.00]
    }
    
    df_ejemplo = pd.DataFrame(ejemplo_data)
    st.subheader("Estructura esperada del archivo Excel:")
    st.dataframe(df_ejemplo, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>🏥 Calculadora ESSALUD - TAMBO | Desarrollado con Streamlit</p>
    <p><small>Esta aplicación procesa datos de ESSALUD según las reglas específicas definidas</small></p>
</div>
""", unsafe_allow_html=True)