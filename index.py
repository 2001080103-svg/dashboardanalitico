from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent


def _buscar_archivo(nombre_fragmento: str, extensiones: tuple[str, ...]) -> Path | None:
    """Busca un archivo por fragmento de nombre en la carpeta del script."""
    nombre_busqueda = nombre_fragmento.lower()
    for ext in extensiones:
        for archivo in BASE_DIR.iterdir():
            if archivo.is_file() and ext.lower() == archivo.suffix.lower() and nombre_busqueda in archivo.name.lower():
                return archivo
    return None


# ==============================================================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Panel de Denuncias Policiales Perú",
    page_icon="🚨",
    layout="wide",
)

st.title("🚨 Panel de Denuncias Policiales del Perú - SIDPOL 2026")
st.markdown(
    "Exploración interactiva del dataset oficial y del diccionario de datos para identificar patrones, tendencias y jurisdicciones con mayor incidencia."
)

# ==============================================================================
# 2. CARGA Y VALIDACIÓN DE DATOS (EXCEL + CSV)
# ==============================================================================
@st.cache_data
def cargar_datos():
    archivo_excel = _buscar_archivo("DICCIONARIO_DATOS_Denuncias_Policiales", (".xlsx", ".xls"))
    archivo_csv = _buscar_archivo("DATASET_Denuncias", (".csv",))

    if archivo_excel is None:
        st.error("No se encontró el archivo Excel del diccionario de datos. Verifica que esté en la misma carpeta que este script.")
        st.stop()

    if archivo_csv is None:
        st.error("No se encontró el archivo CSV del dataset. Verifica que esté en la misma carpeta que este script.")
        st.stop()

    # Leer diccionario de datos
    diccionario = pd.read_excel(archivo_excel, skiprows=3)
    diccionario = diccionario.dropna(subset=["Variable"]).iloc[:, :6]

    # Leer dataset principal
    df = pd.read_csv(archivo_csv, encoding="utf-8-sig")

    columnas_necesarias = {"MES_REGISTRO", "DPTO_HECHO_NEW", "P_MODALIDADES", "cantidad", "UBIGEO_HECHO", "PROV_HECHO", "DIST_HECHO"}
    faltantes = columnas_necesarias - set(df.columns)
    if faltantes:
        st.error(f"Faltan columnas en el dataset: {sorted(faltantes)}")
        st.stop()

    # Mapear número de mes a nombre legible
    meses_map = {
        1: "01 - Enero",
        2: "02 - Febrero",
        3: "03 - Marzo",
        4: "04 - Abril",
        5: "05 - Mayo",
        6: "06 - Junio",
        7: "07 - Julio",
        8: "08 - Agosto",
        9: "09 - Septiembre",
        10: "10 - Octubre",
        11: "11 - Noviembre",
        12: "12 - Diciembre",
    }
    df["MES_NOMBRE"] = df["MES_REGISTRO"].map(meses_map)
    return df, diccionario


df, df_diccionario = cargar_datos()

# ==============================================================================
# 3. BARRA LATERAL DE FILTROS INTERACTIVOS
# ==============================================================================
st.sidebar.header("🔍 Filtros de Búsqueda")

deptos_disponibles = sorted(df["DPTO_HECHO_NEW"].unique())
depto_sel = st.sidebar.multiselect(
    "Departamento / Jurisdicción:",
    options=deptos_disponibles,
    default=[]
)

modalidades_disponibles = sorted(df["P_MODALIDADES"].unique())
mod_sel = st.sidebar.multiselect(
    "Modalidad Delictiva:",
    options=modalidades_disponibles,
    default=[]
)

meses_disponibles = sorted(df["MES_NOMBRE"].unique())
mes_sel = st.sidebar.multiselect(
    "Mes de Registro:",
    options=meses_disponibles,
    default=[]
)

# Aplicar filtros dinámicos
df_filtrado = df.copy()
if depto_sel:
    df_filtrado = df_filtrado[df_filtrado["DPTO_HECHO_NEW"].isin(depto_sel)]
if mod_sel:
    df_filtrado = df_filtrado[df_filtrado["P_MODALIDADES"].isin(mod_sel)]
if mes_sel:
    df_filtrado = df_filtrado[df_filtrado["MES_NOMBRE"].isin(mes_sel)]

# ==============================================================================
# 4. INDICADORES CLAVE DE RENDIMIENTO (KPIs)
# ==============================================================================
total_denuncias = int(df_filtrado["cantidad"].sum())
total_distritos = df_filtrado["UBIGEO_HECHO"].nunique()

if not df_filtrado.empty:
    resumen_depto = df_filtrado.groupby("DPTO_HECHO_NEW")["cantidad"].sum()
    depto_top = resumen_depto.idxmax()
    casos_top = int(resumen_depto.max())

    resumen_mod = df_filtrado.groupby("P_MODALIDADES")["cantidad"].sum()
    mod_top = resumen_mod.idxmax()
else:
    depto_top, casos_top, mod_top = "N/A", 0, "N/A"

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Denuncias Registradas", f"{total_denuncias:,}")
col2.metric("Jurisdicción con Mayor Incidencia", depto_top, f"{casos_top:,} casos")
col3.metric("Modalidad Predominante", mod_top)
col4.metric("Distritos con Reportes", f"{total_distritos:,}")

st.divider()

# ==============================================================================
# 5. VISUALIZACIONES DEL DASHBOARD
# ==============================================================================
if df_filtrado.empty:
    st.warning("No hay registros que coincidan con los filtros seleccionados.")
else:
    fila1_izq, fila1_der = st.columns(2)

    # Gráfico 1: Ranking por Departamento / Jurisdicción
    with fila1_izq:
        st.subheader("Ranking por Departamento / Jurisdicción")
        g_depto = (
            df_filtrado.groupby("DPTO_HECHO_NEW", as_index=False)["cantidad"]
            .sum()
            .sort_values("cantidad", ascending=True)
            .tail(15)
        )
        fig_depto = px.bar(
            g_depto, x="cantidad", y="DPTO_HECHO_NEW", orientation="h",
            text_auto=",", color="cantidad", color_continuous_scale="YlOrRd",
            labels={"cantidad": "Denuncias", "DPTO_HECHO_NEW": "Jurisdicción"}
        )
        fig_depto.update_layout(showlegend=False, coloraxis_showscale=False, height=450)
        st.plotly_chart(fig_depto, use_container_width=True)

    # Gráfico 2: Distribución por Modalidad Delictiva
    with fila1_der:
        st.subheader("Distribución por Modalidad Delictiva")
        g_mod = (
            df_filtrado.groupby("P_MODALIDADES", as_index=False)["cantidad"]
            .sum()
            .sort_values("cantidad", ascending=False)
        )
        fig_mod = px.pie(
            g_mod, names="P_MODALIDADES", values="cantidad", hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_mod.update_traces(textposition="inside", textinfo="percent+label")
        fig_mod.update_layout(showlegend=False, height=450)
        st.plotly_chart(fig_mod, use_container_width=True)

    fila2_izq, fila2_der = st.columns(2)

    # Gráfico 3: Evolución Mensual
    with fila2_izq:
        st.subheader("Evolución Mensual de Denuncias")
        g_mes = (
            df_filtrado.groupby(["MES_REGISTRO", "MES_NOMBRE"], as_index=False)["cantidad"]
            .sum()
            .sort_values("MES_REGISTRO")
        )
        fig_mes = px.line(
            g_mes, x="MES_NOMBRE", y="cantidad", markers=True,
            labels={"MES_NOMBRE": "Mes", "cantidad": "Cantidad de Denuncias"}
        )
        fig_mes.update_traces(line_color="#D95F02", line_width=3, marker_size=8)
        fig_mes.update_layout(height=400)
        st.plotly_chart(fig_mes, use_container_width=True)

    # Gráfico 4: Mapa de Calor (Departamento vs Modalidad)
    with fila2_der:
        st.subheader("Mapa de Calor: Top 10 Jurisdicciones vs. Modalidad")
        top10_nombres = (
            df_filtrado.groupby("DPTO_HECHO_NEW")["cantidad"]
            .sum()
            .nlargest(10)
            .index
        )
        pivote = (
            df_filtrado[df_filtrado["DPTO_HECHO_NEW"].isin(top10_nombres)]
            .pivot_table(index="DPTO_HECHO_NEW", columns="P_MODALIDADES", values="cantidad", aggfunc="sum", fill_value=0)
            .loc[top10_nombres]
        )
        fig_heat = px.imshow(
            pivote, text_auto=",", aspect="auto", color_continuous_scale="YlOrRd",
            labels={"x": "Modalidad", "y": "Jurisdicción", "color": "Casos"}
        )
        fig_heat.update_layout(height=400)
        st.plotly_chart(fig_heat, use_container_width=True)

    # ==========================================================================
    # 6. PESTAÑAS DE TABLA DETALLADA Y DICCIONARIO DE DATOS
    # ==========================================================================
    tab1, tab2 = st.tabs(["📋 Top Distritos y Registros", "📖 Diccionario de Datos (Excel)"])

    with tab1:
        top_distritos = (
            df_filtrado.groupby(["DPTO_HECHO_NEW", "PROV_HECHO", "DIST_HECHO"], as_index=False)["cantidad"]
            .sum()
            .sort_values("cantidad", ascending=False)
            .head(25)
        )
        st.dataframe(top_distritos, use_container_width=True, hide_index=True)

    with tab2:
        st.dataframe(df_diccionario, use_container_width=True, hide_index=True)