import streamlit as st
import pandas as pd
import io
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="Calculadora ESSALUD - TAMBO",
    page_icon="🏥",
    layout="wide"
)

def calcular_importe(row):
    """Función para calcular el importe según las condiciones específicas"""
    if pd.notna(row['fecha_cese']):  # Si hay fecha de cese
        return row['Importe Bruto'] * 0.09
    elif row['Días Subsidio'] > 0:
        return 0  # Corregido: cuando hay días de subsidio, el importe calculado es 0
    elif row['Importe Bruto'] < 1130 and row['Importe Bruto'] > 0:
        return 1130 * 0.09
    else:
        return row['Importe Bruto'] * 0.09

def calcular_calculo_dias_plame(row):
    """Función para calcular CALCULO DIAS PLAME"""
    if row['Días Subsidio'] > 0:
        return round((101.70 / row['Dias_Mes']) * row['DIAS PLAME'], 2)
    else:
        return 0

def procesar_archivo_essalud(df_input):
    """Procesa el archivo aplicando todas las fórmulas de ESSALUD"""
    try:
        df = df_input.copy()
        
        # Convertir fechas
        df['fecha_ingreso'] = pd.to_datetime(df['fecha_ingreso'], format='%d/%m/%Y', errors='coerce')
        df['fecha_cese'] = pd.to_datetime(df['fecha_cese'], format='%d/%m/%Y', errors='coerce')
        
        # Calcular DIAS PLAME
        df['DIAS PLAME'] = df['Dias_Mes'] - df['Días Subsidio']
        
        # Calcular Importe_Calculado
        df['Importe_Calculado'] = df.apply(calcular_importe, axis=1)
        
        # Calcular CALCULO DIAS PLAME
        df['CALCULO DIAS PLAME'] = df.apply(calcular_calculo_dias_plame, axis=1)
        
        # Calcular IMPORTE ESSALUD FINAL
        df['IMPORTE ESSALUD FINAL'] = df[['Importe_Calculado', 'CALCULO DIAS PLAME', 'Importe ESSALUD EJB']].max(axis=1)
        
        return df, None
        
    except Exception as e:
        return None, f"Error al procesar: {str(e)}"

@st.cache_data
def convertir_df_a_excel(df):
    """Convierte DataFrame a Excel para descarga"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Resultados ESSALUD')
    return output.getvalue()

# Título principal
st.title("🏥 Calculadora de ESSALUD - TAMBO")
st.markdown("---")

# Descripción
st.markdown("""
### Descripción
Esta aplicación procesa archivos Excel para calcular los importes de ESSALUD según las reglas específicas de TAMBO.

**Funcionalidades:**
- Cálculo automático de DÍAS PLAME
- Aplicación de fórmulas de ESSALUD según condiciones específicas
- Manejo de fechas de ingreso y cese
- Procesamiento de días de subsidio
- Exportación de resultados en Excel
""")

# Sidebar con instrucciones
with st.sidebar:
    st.header("📋 Instrucciones")
    st.markdown("""
    ### Columnas requeridas en el Excel:
    
    - `fecha_ingreso` (DD/MM/YYYY)
    - `fecha_cese` (DD/MM/YYYY, opcional)
    - `Importe Bruto` (número)
    - `Días Subsidio` (número)
    - `Dias_Mes` (número)
    - `Importe ESSALUD EJB` (número)
    
    ### Proceso:
    1. Sube tu archivo Excel
    2. Revisa los datos
    3. Procesa los cálculos
    4. Descarga el resultado
    """)

# Cargar archivo
st.header("📂 Cargar Archivo Excel")
archivo_subido = st.file_uploader(
    "Selecciona tu archivo Excel",
    type=['xlsx', 'xls'],
    help="El archivo debe contener las columnas requeridas"
)

if archivo_subido is not None:
    try:
        # Leer archivo
        df_original = pd.read_excel(archivo_subido)
        
        st.success("✅ Archivo cargado correctamente")
        
        # Información básica
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Filas", len(df_original))
        with col2:
            st.metric("Columnas", len(df_original.columns))
        with col3:
            st.metric("Tamaño", f"{round(archivo_subido.size/1024, 1)} KB")
        
        # Vista previa
        st.subheader("Vista previa:")
        st.dataframe(df_original.head(), use_container_width=True)
        
        # Verificar columnas
        columnas_requeridas = ['fecha_ingreso', 'fecha_cese', 'Importe Bruto', 'Días Subsidio', 'Dias_Mes', 'Importe ESSALUD EJB']
        columnas_faltantes = [col for col in columnas_requeridas if col not in df_original.columns]
        
        if columnas_faltantes:
            st.error(f"❌ Columnas faltantes: {', '.join(columnas_faltantes)}")
        else:
            st.success("✅ Todas las columnas requeridas están presentes")
            
            # Procesar
            if st.button("🚀 Procesar Cálculos de ESSALUD", type="primary"):
                with st.spinner("Procesando..."):
                    df_resultado, error = procesar_archivo_essalud(df_original)
                    
                    if error:
                        st.error(f"❌ Error: {error}")
                    else:
                        st.success("✅ ¡Procesamiento completado!")
                        
                        # Métricas de resultados
                        st.header("📈 Resultados")
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            total_final = df_resultado['IMPORTE ESSALUD FINAL'].sum()
                            st.metric("Total ESSALUD Final", f"S/ {total_final:,.2f}")
                        
                        with col2:
                            empleados_subsidio = (df_resultado['Días Subsidio'] > 0).sum()
                            st.metric("Empleados con Subsidio", empleados_subsidio)
                        
                        with col3:
                            empleados_cese = df_resultado['fecha_cese'].notna().sum()
                            st.metric("Empleados con Cese", empleados_cese)
                        
                        with col4:
                            promedio_plame = df_resultado['DIAS PLAME'].mean()
                            st.metric("Promedio Días PLAME", f"{promedio_plame:.1f}")
                        
                        # Tabla de resultados
                        st.subheader("Resultados completos:")
                        st.dataframe(df_resultado, use_container_width=True)
                        
                        # Descarga
                        st.header("💾 Descargar Resultados")
                        
                        excel_data = convertir_df_a_excel(df_resultado)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        nombre_archivo = f"essalud_procesado_{timestamp}.xlsx"
                        
                        st.download_button(
                            label="📥 Descargar archivo Excel procesado",
                            data=excel_data,
                            file_name=nombre_archivo,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {str(e)}")

else:
    # Ejemplo de estructura
    st.header("📋 Ejemplo de Estructura")
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
</div>
""", unsafe_allow_html=True)