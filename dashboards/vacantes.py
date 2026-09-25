from utils.core import *
from config.estilos import (
    ESCALA_SEDECO,
    PALETA_SEDECO,
    aplicar_tema_grafica,
)

def dashboard_vacantes():
    df = preparar_vacantes_dashboard(cargar_vacantes_base())

    st.sidebar.title("🎛️ Filtros Vacantes")
    años_disponibles = sorted(df["Año"].dropna().astype(int).unique().tolist(), reverse=True)
    año_actual = pd.Timestamp.today().year
    opciones_año = ["Todos"] + años_disponibles
    indice_año = opciones_año.index(año_actual) if año_actual in opciones_año else 0
    año_seleccionado = st.sidebar.selectbox("Año", opciones_año, index=indice_año)
    estado_seleccionado = st.sidebar.selectbox("Estado", ["Todas"] + ESTADOS_VACANTE)
    empresas = st.sidebar.multiselect("Empresa", sorted(df["Empresa"].dropna().unique()), default=[])
    vacantes = st.sidebar.multiselect("Tipo de vacante", sorted(df["Tipo de Vacante"].dropna().unique()), default=[])

    fecha_min = df["Fecha"].min()
    fecha_max = df["Fecha"].max()
    if pd.isna(fecha_min) or pd.isna(fecha_max):
        fecha_min = pd.Timestamp.today()
        fecha_max = pd.Timestamp.today()
    rango_fechas = st.sidebar.date_input("Rango de fechas", value=(fecha_min, fecha_max), min_value=fecha_min, max_value=fecha_max)

    df_f = df.copy()
    if año_seleccionado != "Todos":
        df_f = df_f[df_f["Año"] == int(año_seleccionado)]
    if estado_seleccionado != "Todas":
        df_f = df_f[df_f["Estado"] == estado_seleccionado]
    if empresas:
        df_f = df_f[df_f["Empresa"].isin(empresas)]
    if vacantes:
        df_f = df_f[df_f["Tipo de Vacante"].isin(vacantes)]
    if len(rango_fechas) == 2:
        inicio = pd.to_datetime(rango_fechas[0])
        fin = pd.to_datetime(rango_fechas[1])
        df_f = df_f[(df_f["Fecha"] >= inicio) & (df_f["Fecha"] <= fin)]

    st.title("💼 Dashboard de Vacantes Consolidadas por Empresa")
    st.markdown("Análisis interactivo de vacantes, empresas vinculadas, fechas de publicación y comportamiento temporal.")

    total_vacantes = len(df_f)
    total_empresas = df_f["Empresa"].nunique()
    total_puestos = df_f["Tipo de Vacante"].nunique()
    meses_activos = df_f["Mes"].nunique()

    c1, c2, c3, c4 = st.columns(4)
    for col, titulo, valor, cap in [
        (c1, "💼 Total vacantes", total_vacantes, "Registros publicados"),
        (c2, "🏢 Empresas", total_empresas, "Empresas únicas"),
        (c3, "🧩 Tipos de puesto", total_puestos, "Vacantes distintas"),
        (c4, "📅 Meses activos", meses_activos, "Periodos con publicación"),
    ]:
        with col:
            with st.container(border=True):
                st.metric(titulo, valor)
                st.caption(cap)
    explicar_visualizacion("Base de vacantes consolidada, después de aplicar año, estado, empresa, tipo y rango de fechas.", "Resume registros de vacantes, empresas únicas, puestos distintos y meses con publicaciones.", "Mide actividad registrada en la base; una vacante es un registro/publicación y no debe interpretarse automáticamente como una contratación.")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        top_empresas = df_f["Empresa"].value_counts().head(12).reset_index(); top_empresas.columns = ["Empresa", "Vacantes"]
        fig = px.bar(top_empresas, x="Vacantes", y="Empresa", orientation="h", text="Vacantes", title="🏆 Top empresas por número de vacantes", color="Vacantes", color_continuous_scale=ESCALA_SEDECO)
        fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis={"categoryorder": "total ascending"}, height=520)
        aplicar_tema_grafica(fig)
        st.plotly_chart(fig, use_container_width=True)
        explicar_visualizacion("Campo 'Empresa' de la base de vacantes filtrada.", "Cuenta registros de vacantes por empresa y muestra las 12 con mayor volumen.", "Las barras más largas identifican empresas con mayor presencia de publicaciones en el periodo seleccionado.")
    with col2:
        top_puestos = df_f["Tipo de Vacante"].value_counts().head(12).reset_index(); top_puestos.columns = ["Tipo de Vacante", "Vacantes"]
        fig = px.bar(top_puestos, x="Vacantes", y="Tipo de Vacante", orientation="h", text="Vacantes", title="🔥 Vacantes más frecuentes", color="Vacantes", color_continuous_scale=ESCALA_SEDECO)
        fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis={"categoryorder": "total ascending"}, height=520)
        aplicar_tema_grafica(fig)
        st.plotly_chart(fig, use_container_width=True)
        explicar_visualizacion("Campo 'Tipo de Vacante' de la base filtrada.", "Cuenta los puestos normalizados más frecuentes.", "Un puesto con mayor barra aparece más veces en la base y refleja mayor recurrencia de publicación, no necesariamente demanda laboral total del mercado.")

    st.subheader("📈 Evolución temporal de vacantes por fecha")
    evolucion = df_f.groupby("Fecha").size().reset_index(name="Vacantes").sort_values("Fecha")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=evolucion["Fecha"], y=evolucion["Vacantes"], mode="lines+markers", line=dict(width=4, color="#AF2140"), marker=dict(size=8, color="#D0B786"), fill="tozeroy", fillcolor="rgba(175,33,64,0.16)", name="Vacantes"))
    fig.update_layout(template="plotly_white", title="Comportamiento de publicaciones a través del tiempo", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=450, xaxis_title="Fecha", yaxis_title="Cantidad de vacantes")
    aplicar_tema_grafica(fig)
    st.plotly_chart(fig, use_container_width=True)
    explicar_visualizacion("Campo 'Fecha' de cada registro de vacante filtrado.", "Cuenta publicaciones por fecha.", "Picos altos indican días con mayor concentración de registros/publicaciones en la base.")

    col3, col4 = st.columns(2)
    with col3:
        mensual = df_f.groupby("Mes").size().reset_index(name="Vacantes").sort_values("Mes")
        fig = px.area(mensual, x="Mes", y="Vacantes", title="📆 Vacantes acumuladas por mes", markers=True, color_discrete_sequence=["#922542"])
        fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=430)
        aplicar_tema_grafica(fig)
        st.plotly_chart(fig, use_container_width=True)
        explicar_visualizacion("Fecha agrupada por mes en la base filtrada.", "Muestra cuántas vacantes fueron registradas en cada mes.", "Permite comparar actividad mensual; valores altos señalan meses con más publicaciones registradas.")
    with col4:
        concentracion = df_f["Empresa"].value_counts(normalize=True).head(10).mul(100).reset_index(); concentracion.columns = ["Empresa", "Porcentaje"]
        fig = px.bar(concentracion, x="Empresa", y="Porcentaje", title="🎯 Concentración de vacantes por empresa (%)", text=concentracion["Porcentaje"].round(1).astype(str) + "%", color="Empresa", color_discrete_sequence=PALETA_SEDECO)
        fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=430, showlegend=False, xaxis_tickangle=-35)
        aplicar_tema_grafica(fig)
        st.plotly_chart(fig, use_container_width=True)
        explicar_visualizacion("Distribución porcentual del campo 'Empresa' en la base filtrada.", "Calcula qué porcentaje de las vacantes pertenece a cada una de las 10 empresas con mayor presencia.", "Una concentración alta en pocas empresas significa que el volumen observado depende fuertemente de ellas.")

    st.subheader("🌡️ Mapa de calor: empresas y meses con más vacantes")
    top_empresas_lista = df_f["Empresa"].value_counts().head(12).index
    heatmap_df = df_f[df_f["Empresa"].isin(top_empresas_lista)]
    tabla_heatmap = pd.pivot_table(heatmap_df, values="Tipo de Vacante", index="Empresa", columns="Mes", aggfunc="count", fill_value=0)
    if not tabla_heatmap.empty:
        fig = px.imshow(tabla_heatmap, text_auto=True, aspect="auto", title="Intensidad de publicaciones por empresa y mes", color_continuous_scale=ESCALA_SEDECO)
        fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=520)
        aplicar_tema_grafica(fig)
        st.plotly_chart(fig, use_container_width=True)
        explicar_visualizacion("Cruce de 'Empresa' y mes derivado de 'Fecha' para las 12 empresas con más vacantes.", "Cada celda cuenta publicaciones de una empresa en un mes.", "Celdas con valores altos localizan combinaciones empresa-mes con mayor actividad de publicación.")

    st.subheader("🧠 Informe automático del dashboard")
    if len(df_f) > 0:
        empresa_top = df_f["Empresa"].value_counts().idxmax(); empresa_top_cant = df_f["Empresa"].value_counts().max()
        vacante_top = df_f["Tipo de Vacante"].value_counts().idxmax(); vacante_top_cant = df_f["Tipo de Vacante"].value_counts().max()
        fecha_top = df_f["Fecha"].value_counts().idxmax(); fecha_top_cant = df_f["Fecha"].value_counts().max()
        mes_top = df_f["Mes"].value_counts().idxmax(); mes_top_cant = df_f["Mes"].value_counts().max()
        st.markdown(f"""
        <div class="insight">
        El periodo analizado contiene <b>{total_vacantes}</b> vacantes publicadas por <b>{total_empresas}</b> empresas diferentes.
        La empresa con mayor presencia es <b>{empresa_top}</b>, con <b>{empresa_top_cant}</b> vacantes registradas.<br><br>
        El puesto más frecuente es <b>{vacante_top}</b>, con <b>{vacante_top_cant}</b> apariciones.
        La fecha con mayor actividad fue <b>{fecha_top.strftime('%d/%m/%Y')}</b>, con <b>{fecha_top_cant}</b> vacantes publicadas.<br><br>
        El mes con mayor movimiento fue <b>{mes_top}</b>, con <b>{mes_top_cant}</b> publicaciones.
        </div>""", unsafe_allow_html=True)
        explicar_visualizacion("Cálculos automáticos sobre la base de vacantes filtrada.", "Resume empresa, puesto, fecha y mes con mayor frecuencia.", "Debe leerse como un resumen descriptivo del conjunto filtrado; no prueba causalidad ni representa por sí solo todo el mercado laboral.")

    st.subheader("🔎 Buscador de vacantes")
    busqueda = st.text_input("Buscar por empresa, puesto, requisitos, beneficios o descripción")
    df_busqueda = df_f.copy()
    if busqueda:
        texto = busqueda.lower()
        df_busqueda = df_busqueda[df_busqueda.astype(str).apply(lambda fila: fila.str.lower().str.contains(texto, na=False).any(), axis=1)]
    st.dataframe(df_busqueda, use_container_width=True, height=420)
    csv = df_busqueda.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Descargar datos filtrados", data=csv, file_name="vacantes_filtradas.csv", mime="text/csv")

# =========================================================
# INGESTA
# =========================================================
