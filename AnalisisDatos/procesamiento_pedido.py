import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# ==============================
# 📌 Funciones de procesamiento
# ==============================

def cargar_datos(archivo_gp, archivo_ax):
    """
    Carga los archivos Excel de GP y AX en dataframes de Pandas.
    
    Parámetros:
    archivo_gp (str): Ruta del archivo GP (Excel).
    archivo_ax (str): Ruta del archivo AX (Excel).

    Retorna:
    tuple: DataFrames de GP y AX.
    """
    df_gp = pd.read_excel(archivo_gp, engine='openpyxl')
    df_ax = pd.read_excel(archivo_ax, engine='openpyxl')
    return df_gp, df_ax

def limpiar_columna(df, columna):
    """
    Limpia una columna específica convirtiéndola en minúsculas y eliminando espacios en blanco.
    También filtra solo valores numéricos y los convierte en enteros.

    Parámetros:
    df (DataFrame): DataFrame a limpiar.
    columna (str): Nombre de la columna a limpiar.

    Retorna:
    DataFrame: DataFrame con la columna limpia.
    """
    df[columna] = df[columna].astype(str).str.strip().str.lower()
    df['is_numeric'] = df[columna].str.isnumeric()
    df_num = df[df['is_numeric']].copy()
    df_num[columna] = df_num[columna].astype(int)
    return df_num

def procesar_datos(df_gp, df_ax):
    """
    Realiza el procesamiento de datos combinando la información de GP y AX.
    Calcula diferencias de tiempo y genera el resumen de datos.

    Parámetros:
    df_gp (DataFrame): Datos del archivo GP.
    df_ax (DataFrame): Datos del archivo AX.

    Retorna:
    tuple: DataFrames de datos combinados, órdenes no unidas, resumen y datos para gráfico de torta.
    """
    # 🔹 Limpiar claves y filtrar solo numéricas
    df_ax_num = limpiar_columna(df_ax, 'N° Orden de compra')
    df_gp_num = limpiar_columna(df_gp, 'Orden de Compra')

    # 🔹 Identificar órdenes sin unir en GP
    ordenes_no_unidas = set(df_gp_num['Orden de Compra']) - set(df_ax_num['N° Orden de compra'])
    df_gp_no_unidas = df_gp_num[df_gp_num['Orden de Compra'].isin(ordenes_no_unidas)].drop_duplicates(subset=['Orden de Compra'])

    # 🔹 Unir datos GP y AX
    df_gp_num = df_gp_num.merge(
        df_ax_num[['N° Orden de compra', 'Id de Origen', 'Fecha y hora de creación', 'Pedido de ventas']],
        left_on='Orden de Compra',
        right_on='N° Orden de compra',
        how='left'
    )

    # 🔹 Ordenar y eliminar duplicados
    df_gp_num = df_gp_num.sort_values(by=['Fecha y hora de creación'], ascending=False).drop_duplicates(subset=['Orden de Compra'], keep='first')
    
    # 🔹 Generar DataFrame combinado sin las órdenes no unidas
    df_combinado = df_gp_num[~df_gp_num['Orden de Compra'].isin(ordenes_no_unidas)].copy()

    # 🔹 Calcular diferencias de tiempo
    df_combinado['Fecha Trx'] = pd.to_datetime(df_combinado['Fecha Trx'], errors='coerce')
    df_combinado['Fecha y hora de creación'] = pd.to_datetime(df_combinado['Fecha y hora de creación'], errors='coerce')
    df_combinado['Dias_entre_GP_y_AX'] = (df_combinado['Fecha y hora de creación'] - df_combinado['Fecha Trx']).dt.days.fillna(0).astype(int)
    df_combinado['Categoria_Dias'] = df_combinado['Dias_entre_GP_y_AX'].apply(lambda x: "0 Días" if x == 0 else "1 Día o más")

    # 🔹 Seleccionar columnas finales para el informe
    df_combinado = df_combinado[['Orden de Compra', 'Cantidad', 'Valor SKU Total', 'Fecha Trx', 
                                 'Fecha y hora de creación', 'Id de Origen', 'Pedido de ventas', 'Categoria_Dias']]

    # 🔹 Generar resumen
    resumen = {
        "Métrica": [
            "Total de registros (GP)",
            "Órdenes únicas en GP",
            "Órdenes únicas en AX",
            "Órdenes comunes entre GP y AX",
            "Órdenes sin unir en GP"
        ],
        "Cantidad": [
            len(df_gp),
            df_gp_num['Orden de Compra'].nunique(),
            df_ax_num['N° Orden de compra'].nunique(),
            len(set(df_combinado['Orden de Compra']) & set(df_ax_num['N° Orden de compra'])),
            len(df_gp_no_unidas)
        ]
    }
    df_resumen = pd.DataFrame(resumen)

    # 🔹 Datos para gráfico de torta
    df_pie = pd.DataFrame({
        "Métrica": ["Órdenes Cruzadas", "Órdenes No Cruzadas"],
        "Cantidad": [resumen["Cantidad"][3], resumen["Cantidad"][4]]
    })

    return df_combinado, df_gp_no_unidas, df_resumen, df_pie

# ======================================
# 📊 INTERFAZ STREAMLIT - APLICACIÓN
# ======================================

st.title("📊 Análisis de Pedidos entre GP y AX")

# 📂 Cargar archivos
archivo_gp = st.file_uploader("📂 Sube el archivo GP (Excel o CSV)", type=['xlsx', 'csv'])
archivo_ax = st.file_uploader("📂 Sube el archivo AX (Excel o CSV)", type=['xlsx', 'csv'])

if archivo_gp and archivo_ax:
    # Procesamiento de datos
    df_gp, df_ax = cargar_datos(archivo_gp, archivo_ax)
    df_combinado, df_gp_no_unidas, df_resumen, df_pie = procesar_datos(df_gp, df_ax)

    # 📌 Mostrar resultados
    st.subheader("📌 Resumen General")
    st.dataframe(df_resumen)

    st.subheader("📌 Datos Combinados")
    st.dataframe(df_combinado)

    st.subheader("📌 Órdenes No Unidas")
    st.dataframe(df_gp_no_unidas)

    # 📊 Gráfico de torta
    st.subheader("📊 Porcentaje de Pedidos en AX")
    fig_pie = px.pie(df_pie, values='Cantidad', names='Métrica',
                     title='Órdenes Cruzadas vs No Cruzadas', hole=0.4,
                     color_discrete_sequence=["darkorange", "royalblue"])
    st.plotly_chart(fig_pie)

    # 📊 Gráfico de barras por origen y tiempo
    st.subheader("📊 Distribución de Órdenes por Tiempo entre GP y AX")
    df_conteo_dias = df_combinado.groupby(["Id de Origen", "Categoria_Dias"])['Orden de Compra'].count().reset_index()
    fig = px.bar(df_conteo_dias, x="Id de Origen", y="Orden de Compra", color="Categoria_Dias",
                 title="Órdenes por Origen y Tiempo de Demora",
                 color_discrete_map={"0 Días": "royalblue", "1 Día o más": "darkorange"})
    st.plotly_chart(fig)

    # 📊 Exportar informe a Excel
    fecha_actual = datetime.now().strftime('%Y-%m-%d')
    nombre_archivo = f"Reporte_{fecha_actual}.xlsx"
    with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
        df_resumen.to_excel(writer, sheet_name='Resumen General', index=False)
        df_combinado.to_excel(writer, sheet_name='Datos Combinados', index=False)
        df_gp_no_unidas.to_excel(writer, sheet_name='Órdenes No Unidas', index=False)

    with open(nombre_archivo, "rb") as file:
        st.download_button(label="📥 Descargar Reporte Excel", data=file, file_name=nombre_archivo, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
