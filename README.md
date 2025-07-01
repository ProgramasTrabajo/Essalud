# 🏥 Calculadora ESSALUD - TAMBO

Una aplicación web desarrollada en Streamlit para procesar y calcular automáticamente los importes de ESSALUD según las reglas específicas de TAMBO.

## 🚀 Características

- **Procesamiento automático**: Calcula importes de ESSALUD basado en reglas específicas
- **Interfaz intuitiva**: Aplicación web fácil de usar desarrollada con Streamlit
- **Manejo de fechas**: Procesamiento automático de fechas de ingreso y cese
- **Cálculos especializados**: Aplicación de fórmulas específicas para días de subsidio
- **Exportación de resultados**: Descarga de archivos Excel procesados
- **Validación de datos**: Verificación automática de columnas requeridas

## 📋 Funcionalidades

### Cálculos Implementados

1. **DÍAS PLAME**: Días del mes - Días subsidio
2. **Importe Calculado**: Aplicación de reglas según condiciones:
   - Con fecha de cese: Importe Bruto × 9%
   - Con días de subsidio > 0: 1130 × 9%
   - Importe < 1130: 1130 × 9%
   - Importe ≥ 1130: Importe Bruto × 9%
3. **Cálculo Días PLAME**: (101.70 / Días del mes) × DÍAS PLAME
4. **Importe ESSALUD Final**: Valor mayor entre las columnas calculadas

### Estructura de Datos Requerida

El archivo Excel debe contener las siguientes columnas:

- `fecha_ingreso` (formato: DD/MM/YYYY)
- `fecha_cese` (formato: DD/MM/YYYY, puede estar vacío)
- `Importe Bruto` (número)
- `Días Subsidio` (número)
- `Dias_Mes` (número)
- `Importe ESSALUD EJB` (número)

## 🛠️ Instalación y Uso

### Instalación Local

1. Clona el repositorio:
```bash
git clone <tu-repositorio>
cd calculadora-essalud-tambo
```

2. Instala las dependencias:
```bash
pip install streamlit pandas openpyxl xlsxwriter
```

3. Ejecuta la aplicación:
```bash
streamlit run streamlit_app.py
```

### Despliegue en Streamlit Cloud

1. Sube tu código a GitHub
2. Ve a [share.streamlit.io](https://share.streamlit.io)
3. Conecta tu repositorio de GitHub
4. Configura el archivo principal como `streamlit_app.py`
5. Despliega la aplicación

## 📊 Uso de la Aplicación

1. **Cargar archivo**: Sube tu archivo Excel con los datos de empleados
2. **Verificar datos**: Revisa la vista previa y verifica que todas las columnas estén presentes
3. **Procesar**: Haz clic en "Procesar Cálculos de ESSALUD"
4. **Revisar resultados**: Analiza las métricas y la tabla de resultados
5. **Descargar**: Obtén el archivo Excel procesado con todos los cálculos

## 🔧 Configuraciones

### Variables de Cálculo

- **Factor ESSALUD**: 9% (0.09)
- **Importe mínimo**: S/ 1,130
- **Factor días PLAME**: 101.70

### Opciones de Visualización

- **Mostrar detalles**: Activar para ver análisis detallados por subsidio y cese
- **Métricas en tiempo real**: Visualización de estadísticas importantes
- **Exportación personalizada**: Nombres de archivo con timestamp

## 📈 Ejemplos de Uso

### Ejemplo de Datos de Entrada

| fecha_ingreso | fecha_cese | Importe Bruto | Días Subsidio | Dias_Mes | Importe ESSALUD EJB |
|---------------|------------|---------------|---------------|----------|-------------------|
| 01/01/2023    |            | 1200.00       | 0             | 30       | 108.00            |
| 15/02/2023    | 31/12/2023 | 800.00        | 5             | 30       | 72.00             |
| 30/03/2023    |            | 1500.00       | 0             | 30       | 135.00            |

### Resultados Esperados

La aplicación calculará automáticamente:
- DÍAS PLAME para cada empleado
- Importe calculado según las reglas
- Cálculo específico para días PLAME
- Importe ESSALUD final (valor máximo)

## 🚀 Deployment en Streamlit Cloud

### Pasos para Publicar

1. **Preparar el repositorio**:
   - Asegúrate de que `streamlit_app.py` esté en la raíz
   - Verifica que todas las dependencias estén instaladas

2. **Configurar GitHub**:
   - Crea un repositorio público en GitHub
   - Sube todo el código incluyendo `streamlit_app.py`

3. **Desplegar en Streamlit**:
   - Ve a [share.streamlit.io](https://share.streamlit.io)
   - Haz clic en "New app"
   - Conecta tu cuenta de GitHub
   - Selecciona el repositorio y la rama
   - Especifica `streamlit_app.py` como archivo principal
   - Haz clic en "Deploy"

4. **Configurar dominio** (opcional):
   - Una vez desplegada, obtendrás una URL como `https://tu-app.streamlit.app`
   - Puedes personalizar el nombre de la aplicación en la configuración

### Requisitos para el Deployment

- Cuenta de GitHub (gratuita)
- Cuenta de Streamlit Cloud (gratuita)
- Repositorio público en GitHub

## 📝 Notas Técnicas

### Dependencias Principales

```python
streamlit==1.46.1
pandas==2.1.4
openpyxl==3.1.2
xlsxwriter==3.2.5
```

### Estructura del Proyecto

```
calculadora-essalud-tambo/
├── streamlit_app.py          # Aplicación principal
├── README.md                 # Documentación
└── pyproject.toml           # Configuración de dependencias
```

## 🤝 Contribución

Si deseas contribuir al proyecto:

1. Haz fork del repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-caracteristica`)
3. Commit tus cambios (`git commit -am 'Agregar nueva característica'`)
4. Push a la rama (`git push origin feature/nueva-caracteristica`)
5. Crea un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 📞 Soporte

Para reportar bugs o solicitar nuevas características, por favor crea un issue en el repositorio de GitHub.

---

**Desarrollado con ❤️ usando Streamlit**