import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

def cargar_datos(archivo_gp, archivo_ax):
    df_gp = pd.read_excel(archivo_gp, engine='openpyxl')
    df_ax = pd.read_excel(archivo_ax, engine='openpyxl')
    return df_gp, df_ax

def limpiar_columna(df, columna):
    df[columna] = df[columna].astype(str).str.strip().str.lower()
    df['is_numeric'] = df[columna].str.isnumeric()
    df_num = df[df['is_numeric']].copy()
    df_num[columna] = df_num[columna].astype(int)
    return df_num

def procesar_datos(df_gp, df_ax):
    df_ax_num = limpiar_columna(df_ax, 'N° Orden de compra')
    df_gp_num = limpiar_columna(df_gp, 'Orden de Compra')
    
    ordenes_no_unidas = set(df_gp_num['Orden de Compra']) - set(df_ax_num['N° Orden de compra'])
    df_gp_no_unidas = df_gp_num[df_gp_num['Orden de Compra'].isin(ordenes_no_unidas)].drop_duplicates(subset=['Orden de Compra'])
    total_ordenes_no_unidas = len(df_gp_no_unidas)
    
    df_ax_num = df_ax_num.drop_duplicates(subset=['N° Orden de compra'])
    df_gp_num = df_gp_num.drop_duplicates(subset=['Orden de Compra'])
    
    df_gp_num = df_gp_num.merge(
        df_ax_num[['N° Orden de compra', 'Id de Origen', 'Fecha y hora de creación', 'Pedido de ventas']],
        left_on='Orden de Compra',
        right_on='N° Orden de compra',
        how='left'
    )
    df_gp_num = df_gp_num.sort_values(by=['Fecha y hora de creación'], ascending=False).drop_duplicates(subset=['Orden de Compra'], keep='first')
    df_combinado = df_gp_num[~df_gp_num['Orden de Compra'].isin(ordenes_no_unidas)].copy()
    
    df_combinado['Fecha Trx'] = pd.to_datetime(df_combinado['Fecha Trx'], errors='coerce')
    df_combinado['Fecha y hora de creación'] = pd.to_datetime(df_combinado['Fecha y hora de creación'], errors='coerce')
    df_combinado['Dias_entre_GP_y_AX'] = (df_combinado['Fecha y hora de creación'] - df_combinado['Fecha Trx']).dt.days.fillna(0).astype(int)
    df_combinado['Categoria_Dias'] = df_combinado['Dias_entre_GP_y_AX'].apply(lambda x: "0 Días" if x == 0 else "1 Día o más")
    df_combinado = df_combinado[['Orden de Compra', 'Cantidad', 'Valor SKU Total', 'Fecha Trx', 'Fecha y hora de creación', 'Id de Origen', 'Pedido de ventas','Categoria_Dias','Dias_entre_GP_y_AX']]
    
    total_gp = len(df_gp)
    ordenes_gp_unicas = df_gp_num['Orden de Compra'].nunique()
    ordenes_ax_unicas = df_ax_num['N° Orden de compra'].nunique()
    ordenes_comunes = len(set(df_combinado['Orden de Compra']) & set(df_ax_num['N° Orden de compra']))
    
    resumen = {
        "Métrica": [
            "Total de registros (GP)",
            "Órdenes únicas en GP",
            "Órdenes únicas en AX",
            "Órdenes comunes entre GP y AX",
            "Órdenes sin unir en GP"
        ],
        "Cantidad": [
            total_gp,
            ordenes_gp_unicas,
            ordenes_ax_unicas,
            ordenes_comunes,
            total_ordenes_no_unidas
        ]
    }
    df_resumen = pd.DataFrame(resumen)
    
    df_pie = pd.DataFrame({
        "Métrica": ["Órdenes Cruzadas", "Órdenes No Cruzadas"],
        "Cantidad": [ordenes_comunes, total_ordenes_no_unidas]
    })
    
    return df_combinado, df_gp_no_unidas, df_resumen, df_pie

st.title("📊 Análisis de Pedidos entre GP y AX")

st.markdown("<h3>📂 Sube el archivo GP</h3>", unsafe_allow_html=True)
archivo_gp = st.file_uploader("📂 Arrastra y suelta tu archivo aquí o haz clic en 'Explorar archivos'", 
                              type=['xlsx', 'csv'], key="archivo_gp")

st.markdown("<h3>📂 Sube el archivo AX</h3>", unsafe_allow_html=True)
archivo_ax = st.file_uploader("📂 Arrastra y suelta tu archivo aquí o haz clic en 'Explorar archivos'", 
                              type=['xlsx', 'csv'], key="archivo_ax")




if archivo_gp and archivo_ax:
    df_gp, df_ax = cargar_datos(archivo_gp, archivo_ax)
    df_combinado, df_gp_no_unidas, df_resumen, df_pie = procesar_datos(df_gp, df_ax)
    
    st.subheader("📌 Resumen General")
    st.dataframe(df_resumen)
    
    st.subheader("📌 Datos Combinados")
    st.dataframe(df_combinado)
    
    st.subheader("📌 Órdenes No Unidas")
    st.dataframe(df_gp_no_unidas)
    
    st.subheader("📊 Porcentaje de Pedidos en AX")
    fig_pie = px.pie(df_pie, values='Cantidad', names='Métrica',
                    title='Órdenes Cruzadas vs No Cruzadas', hole=0.4,
                    color_discrete_sequence=["darkorange", "royalblue"])  # 🔹 Colores fijos
    st.plotly_chart(fig_pie)

    st.subheader("📊 Distribución de Órdenes por Tiempo entre GP y AX")
    df_filtrado = df_combinado[df_combinado["Id de Origen"].isin(["Vent.Verde", "Eco.Mag"])]
    df_filtrado["Categoria_Dias"] = df_filtrado["Dias_entre_GP_y_AX"].apply(lambda x: "0 Días" if x == 0 else "1 Día o más")
    df_conteo_dias = df_filtrado.groupby(["Id de Origen", "Categoria_Dias"])['Orden de Compra'].count().reset_index()
    df_conteo_dias['Porcentaje'] = df_conteo_dias['Orden de Compra'] / df_conteo_dias.groupby('Id de Origen')['Orden de Compra'].transform('sum') * 100

    fig = px.bar(df_conteo_dias, x="Id de Origen", y="Orden de Compra", color="Categoria_Dias",
                title="Órdenes por Origen y Tiempo de Demora",
                text=df_conteo_dias.apply(lambda row: f"{row['Orden de Compra']} ({row['Porcentaje']:.1f}%)", axis=1),
                barmode="group", labels={"Orden de Compra": "Cantidad de Órdenes"},
                color_discrete_map={"0 Días": "royalblue", "1 Día o más": "darkorange"})  # 🔹 Colores fijos
    st.plotly_chart(fig)

    st.subheader("📊 Tiempo entre GP vs AX")
    df_categoria_final = df_combinado['Categoria_Dias'].value_counts().reset_index()
    df_categoria_final.columns = ['Categoria_Dias', 'Cantidad']
    df_categoria_final['Porcentaje'] = (df_categoria_final['Cantidad'] / df_categoria_final['Cantidad'].sum()) * 100

    fig_final = px.bar(df_categoria_final, x='Categoria_Dias', y='Porcentaje',
                    text=df_categoria_final.apply(lambda row: f"{row['Cantidad']} ({row['Porcentaje']:.2f}%)", axis=1),
                    labels={'Categoria_Dias': 'Categoría de Días', 'Porcentaje': 'Porcentaje de Órdenes'},
                    title='Distribución Final de Órdenes', color='Categoria_Dias',
                    color_discrete_map={"0 Días": "royalblue", "1 Día o más": "darkorange"})  # 🔹 Colores fijos
    st.plotly_chart(fig_final)

    fecha_actual = datetime.now().strftime('%Y-%m-%d')
    nombre_archivo = f"Reporte_{fecha_actual}.xlsx"
    with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
        df_resumen.to_excel(writer, sheet_name='Resumen General', index=False)
        df_combinado.to_excel(writer, sheet_name='Datos Combinados', index=False)
        df_gp_no_unidas.to_excel(writer, sheet_name='Órdenes No Unidas', index=False)
    
    with open(nombre_archivo, "rb") as file:
        st.download_button(label="📥 Descargar Reporte Excel", data=file, file_name=nombre_archivo, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")