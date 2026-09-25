from utils.core import *
from config.estilos import ESCALA_SEDECO, PALETA_SEDECO, aplicar_tema_grafica


def _visual(serie):
    s = serie.fillna("").astype(str).str.strip()
    return s.mask(s.eq(""), "Sin dato")


def _metric_card(col, label, value, caption):
    with col:
        with st.container(border=True):
            st.metric(label, value)
            st.caption(caption)


def _tabla_anual(df):
    con_año = df[df["año"].notna()].copy()
    if con_año.empty:
        return pd.DataFrame(columns=["Año", "Personas únicas", "Vinculaciones", "Promedio por persona", "Personas recurrentes"])
    filas = []
    for año, g in con_año.groupby("año"):
        conteos = g.groupby("id_persona_maestro").size()
        filas.append({
            "Año": int(año),
            "Personas únicas": int(g["id_persona_maestro"].nunique()),
            "Vinculaciones": int(len(g)),
            "Promedio por persona": round(len(g) / max(g["id_persona_maestro"].nunique(), 1), 2),
            "Personas recurrentes": int((conteos > 1).sum()),
        })
    return pd.DataFrame(filas).sort_values("Año")


def dashboard_personas():
    df = preparar_personas_dashboard(cargar_personas_base())
    if df.empty:
        st.title("🎓 Personas y Vinculaciones")
        st.info("No hay registros en la base de personas.")
        return

    df_f = df.copy()
    st.sidebar.title("🎛️ Filtros Personas")
    filtros = ["sexo", "escolaridad", "carrera", "Institución", "municipio", "grupo_prioritario", "vinculacion"]
    for col in filtros:
        if col == "municipio":
            presentes = list(_visual(df[col]).unique())
            opciones = list(OPCIONES_UBICACION_FILTRO)
            for valor in presentes:
                if valor not in opciones:
                    opciones.append(valor)
        else:
            opciones = sorted(_visual(df[col]).unique())
        seleccion = st.sidebar.multiselect(col, opciones, default=[], key=f"fp_{col}")
        if seleccion:
            serie = _visual(df_f[col])
            df_f = df_f[serie.isin(seleccion)]
    años = sorted(pd.to_numeric(df["Año"], errors="coerce").dropna().astype(int).unique())
    sel_años = st.sidebar.multiselect("Año", años, default=[], key="fp_año")
    if sel_años:
        df_f = df_f[pd.to_numeric(df_f["Año"], errors="coerce").isin(sel_años)]

    st.title("👥 Personas y Vinculaciones")
    st.markdown(
        "Cada **persona maestra** se cuenta una sola vez, mientras que cada fila histórica se conserva como una **vinculación**. "
        "Así una persona puede tener múltiples vinculaciones sin perder su historial."
    )
    st.success("Estado actual: **todas las vinculaciones históricas están marcadas como Vinculado**. Los campos faltantes se muestran como Sin dato.")

    total_vinc = len(df_f)
    total_personas = df_f["id_persona_maestro"].nunique()
    resumen = df_f.groupby("id_persona_maestro").size()
    recurrentes = int((resumen > 1).sum())
    max_vinc = int(resumen.max()) if len(resumen) else 0
    sin_año = int(pd.to_numeric(df_f["Año"], errors="coerce").isna().sum())
    promedio = total_vinc / total_personas if total_personas else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    _metric_card(c1, "👤 Personas únicas", f"{total_personas:,}", "ID persona maestro")
    _metric_card(c2, "🔗 Vinculaciones", f"{total_vinc:,}", "Registros históricos")
    _metric_card(c3, "🔁 Recurrentes", f"{recurrentes:,}", "Personas con 2+ vinculaciones")
    _metric_card(c4, "📈 Vinculaciones/persona", f"{promedio:.2f}", "Promedio del filtro")
    _metric_card(c5, "🏅 Máximo", max_vinc, "Vinculaciones de una persona")
    _metric_card(c6, "📅 Sin año", f"{sin_año:,}", "Históricos sin fecha/año")
    explicar_visualizacion(
        "Base de personas, después de aplicar los filtros activos del panel.",
        "Las métricas distinguen personas únicas por ID maestro de vinculaciones históricas (filas), y calculan recurrencia, promedio, máximo y registros sin año.",
        "Si el promedio de vinculaciones por persona supera 1 hay recurrencia. 'Sin año' señala registros que no deben usarse para comparar periodos hasta completar su fecha o año."
    )

    st.divider()
    vista = st.radio(
        "Vista",
        ["📊 Resumen", "📅 Evolución anual", "🔁 Recurrencia", "👤 Historial por persona", "🎓 Perfil"],
        horizontal=True,
        key="dashboard_personas_vista",
        label_visibility="collapsed",
    )

    if vista == "📊 Resumen":
        col1, col2 = st.columns(2)
        with col1:
            tipos = _visual(df_f["vinculacion"]).value_counts().reset_index()
            tipos.columns = ["Tipo", "Vinculaciones"]
            fig = px.bar(tipos, x="Vinculaciones", y="Tipo", orientation="h", text="Vinculaciones",
                         title="Vinculaciones por tipo", color="Vinculaciones", color_continuous_scale=ESCALA_SEDECO)
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=420)
            aplicar_tema_grafica(fig); st.plotly_chart(fig, use_container_width=True)
            explicar_visualizacion("Campo 'vinculacion' de la base de personas filtrada.", "Cuenta cuántas vinculaciones históricas existen en cada tipo.", "Una barra mayor indica que ese tipo concentra más registros de vinculación dentro del filtro actual.")
        with col2:
            dist = resumen.value_counts().sort_index().reset_index()
            dist.columns = ["Vinculaciones por persona", "Personas"]
            dist["Grupo"] = dist["Vinculaciones por persona"].astype(str) + " vinculaciones"
            fig = px.bar(dist, x="Grupo", y="Personas", text="Personas", title="Frecuencia de vinculaciones por persona",
                         color="Personas", color_continuous_scale=ESCALA_SEDECO)
            aplicar_tema_grafica(fig); st.plotly_chart(fig, use_container_width=True)
            explicar_visualizacion("Conteo de filas por 'id_persona_maestro' en la base de personas filtrada.", "Agrupa a las personas según el número de vinculaciones históricas que tienen.", "Permite distinguir casos únicos de personas recurrentes; desplazamientos hacia valores mayores significan mayor recurrencia.")

        top = resumen.sort_values(ascending=False).head(15).rename("Vinculaciones").reset_index()
        nombres = obtener_personas_maestras(df_f)[["id_persona_maestro", "nombre"]].drop_duplicates("id_persona_maestro")
        top = top.merge(nombres, on="id_persona_maestro", how="left")
        top = top[["id_persona_maestro", "nombre", "Vinculaciones"]]
        st.subheader("Personas con mayor número de vinculaciones")
        st.dataframe(top, use_container_width=True, hide_index=True)

    if vista == "📅 Evolución anual":
        anual = _tabla_anual(df_f)
        if anual.empty:
            st.info("No hay registros con año disponible para este filtro.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                fig = px.line(anual, x="Año", y=["Personas únicas", "Vinculaciones"], markers=True,
                              title="Personas únicas vs. vinculaciones por año")
                fig.update_layout(legend_title_text="Indicador", height=430)
                aplicar_tema_grafica(fig); st.plotly_chart(fig, use_container_width=True)
                explicar_visualizacion("Año/fecha, ID maestro y filas históricas de la base de personas filtrada.", "Compara personas únicas y vinculaciones registradas en cada año.", "Cuando las vinculaciones crecen más que las personas únicas, aumenta la recurrencia o repetición de atención/vinculación por persona.")
            with c2:
                tipo_anual = df_f[df_f["año"].notna()].copy()
                tipo_anual["Tipo"] = _visual(tipo_anual["vinculacion"])
                tipo_anual = tipo_anual.groupby(["año", "Tipo"]).size().reset_index(name="Vinculaciones")
                fig = px.bar(tipo_anual, x="año", y="Vinculaciones", color="Tipo", barmode="stack",
                             title="Composición anual por tipo", color_discrete_sequence=PALETA_SEDECO)
                aplicar_tema_grafica(fig); st.plotly_chart(fig, use_container_width=True)
                explicar_visualizacion("Campos 'Año' y 'vinculacion' de la base de personas filtrada.", "Muestra la composición anual de vinculaciones por tipo.", "Permite observar qué tipos explican el volumen de cada año y detectar cambios en la mezcla de servicios o procesos de vinculación.")
            st.subheader("Indicadores anuales")
            st.dataframe(anual, use_container_width=True, hide_index=True)
            st.caption(f"Además existen {sin_año:,} vinculaciones sin año disponible; se conservan y no se asignan artificialmente a un periodo.")

    if vista == "🔁 Recurrencia":
        resumen_persona = resumen_vinculaciones_por_persona(df_f)
        if resumen_persona.empty:
            st.info("Sin datos para analizar recurrencia.")
        else:
            recurrentes_df = resumen_persona[resumen_persona["total_vinculaciones"] > 1].copy()
            c1, c2, c3 = st.columns(3)
            c1.metric("Personas con 1 vinculación", int((resumen_persona["total_vinculaciones"] == 1).sum()))
            c2.metric("Personas con 2+ vinculaciones", len(recurrentes_df))
            c3.metric("% recurrentes", f"{len(recurrentes_df)/len(resumen_persona)*100:.1f}%")
            explicar_visualizacion("Conteo de vinculaciones por ID persona maestro.", "Separa personas con una sola vinculación de quienes tienen dos o más y calcula su proporción.", "Un porcentaje recurrente alto indica que una parte importante de las personas aparece en más de un proceso histórico de vinculación.")
            st.dataframe(recurrentes_df, use_container_width=True, hide_index=True, height=460)
            st.download_button("⬇️ Descargar recurrencia", recurrentes_df.to_csv(index=False).encode("utf-8-sig"),
                               "personas_recurrentes.csv", "text/csv")

    if vista == "👤 Historial por persona":
        maestras = obtener_personas_maestras(df_f)
        maestras = maestras.sort_values(["nombre", "id_persona_maestro"])
        opciones = list(maestras.index)
        idx = st.selectbox(
            "Selecciona una persona",
            opciones,
            format_func=lambda i: f"{maestras.loc[i, 'nombre']} — {maestras.loc[i, 'id_persona_maestro']} — {int(maestras.loc[i, 'total_vinculaciones'])} vinculaciones",
            key="historial_persona_maestra",
        )
        persona = maestras.loc[idx]
        mid = persona["id_persona_maestro"]
        hist = df_f[df_f["id_persona_maestro"].eq(mid)].copy()
        hist = hist.sort_values(["fecha_registro", "id_persona"], na_position="last")

        st.subheader(f"{persona['nombre']}")
        st.caption(f"ID maestro: {mid}")
        a, b, c, d = st.columns(4)
        a.metric("Vinculaciones", len(hist))
        b.metric("Tipos distintos", hist["vinculacion"].replace("", pd.NA).nunique())
        años_hist = pd.to_numeric(hist["Año"], errors="coerce").dropna().astype(int)
        c.metric("Años con registro", años_hist.nunique())
        d.metric("Último año", int(años_hist.max()) if len(años_hist) else "Sin dato")
        explicar_visualizacion("Historial de la persona seleccionada en la base de personas.", "Resume cantidad de vinculaciones, diversidad de tipos y cobertura temporal de esa persona.", "Sirve para leer su trayectoria: más vinculaciones o más años registrados implican mayor recurrencia histórica, no necesariamente múltiples empleos.")

        datos = {
            "Sexo": persona.get("sexo", ""), "Edad": persona.get("edad", ""),
            "Municipio": persona.get("municipio", ""), "Institución": persona.get("Institución", ""),
            "Carrera": persona.get("carrera", ""), "Teléfono": persona.get("telefono", ""), "Correo": persona.get("correo", "")
        }
        st.markdown("**Datos de referencia de la persona**")
        cols = st.columns(3)
        for n, (k, v) in enumerate(datos.items()):
            valor = "Sin dato" if pd.isna(v) or str(v).strip() == "" else str(v)
            cols[n % 3].markdown(f"**{k}:** {valor}")

        mostrar = hist[["id_persona", "vinculacion", "fecha_registro", "Año", "Institución", "carrera", "municipio", "telefono", "correo", "estatus_vinculacion"]].copy()
        mostrar["fecha_registro"] = pd.to_datetime(mostrar["fecha_registro"], errors="coerce").dt.strftime("%d/%m/%Y").fillna("Sin dato")
        for col in ["vinculacion", "Año", "Institución", "carrera", "municipio", "telefono", "correo"]:
            mostrar[col] = mostrar[col].apply(lambda v: "Sin dato" if pd.isna(v) or str(v).strip() in ["", "nan", "NaT"] else v)
        mostrar["estatus_vinculacion"] = "Vinculado"
        mostrar = mostrar.rename(columns={"id_persona": "ID vinculación histórica", "vinculacion": "Tipo de vinculación", "fecha_registro": "Fecha", "estatus_vinculacion": "Estatus"})
        st.markdown("**Historial completo de vinculaciones**")
        st.dataframe(mostrar, use_container_width=True, hide_index=True)

        seguimientos = limpiar_vinculaciones(cargar_vinculaciones_base())
        seg = seguimientos[seguimientos["id_persona_maestro"].eq(mid)].copy()
        if not seg.empty:
            st.markdown("**Seguimientos con empresas/vacantes**")
            st.dataframe(seg, use_container_width=True, hide_index=True)

    if vista == "🎓 Perfil":
        maestras_perfil = obtener_personas_maestras(df_f).copy()

        sexo = _visual(maestras_perfil["sexo"]).value_counts().reset_index()
        sexo.columns = ["Sexo", "Personas"]
        fig = px.pie(sexo, names="Sexo", values="Personas", hole=.52, title="Personas únicas por sexo",
                     color_discrete_sequence=PALETA_SEDECO)
        aplicar_tema_grafica(fig); st.plotly_chart(fig, use_container_width=True)
        explicar_visualizacion("Campo 'sexo' de una fila representativa por ID persona maestro.", "Distribuye personas únicas por sexo registrado.", "Cada porción representa la proporción de personas únicas en esa categoría; 'Sin dato' indica información faltante.")

        # Siempre se muestran los 60 municipios de Tlaxcala, incluso con valor 0.
        maestras_perfil["municipio_v"] = maestras_perfil["municipio"].apply(normalizar_ubicacion_mexico)
        conteo_muni = maestras_perfil[maestras_perfil["municipio_v"].isin(MUNICIPIOS_TLAXCALA)]["municipio_v"].value_counts()
        muni = pd.DataFrame({"Municipio": MUNICIPIOS_TLAXCALA})
        muni["Personas"] = muni["Municipio"].map(conteo_muni).fillna(0).astype(int)
        muni["Etiqueta"] = muni["Personas"].where(muni["Personas"] > 0, "")
        fig = px.bar(
            muni, x="Personas", y="Municipio", orientation="h", text="Etiqueta",
            title="60 municipios de Tlaxcala — personas únicas",
            color="Personas", color_continuous_scale=ESCALA_SEDECO,
        )
        fig.update_layout(height=1500, yaxis={"categoryorder": "array", "categoryarray": list(reversed(MUNICIPIOS_TLAXCALA))})
        fig.update_traces(hovertemplate="<b>%{y}</b><br>Personas únicas: %{x}<extra></extra>")
        aplicar_tema_grafica(fig); st.plotly_chart(fig, use_container_width=True)
        explicar_visualizacion("Municipio normalizado de una fila por persona maestra; se incluyen los 60 municipios de Tlaxcala aunque tengan valor cero.", "Cuenta personas únicas asociadas a cada municipio.", "Barras mayores indican más personas registradas en ese municipio; cero significa que no hay personas en el filtro actual, no que el municipio no exista.")

        col3, col4 = st.columns(2)
        with col3:
            inst = maestras_perfil.copy(); inst["inst_v"] = _visual(inst["Institución"])
            inst = inst["inst_v"].value_counts().head(12).reset_index(); inst.columns = ["Institución", "Personas"]
            fig = px.bar(inst, x="Personas", y="Institución", orientation="h", text="Personas", title="Instituciones — personas únicas",
                         color="Personas", color_continuous_scale=ESCALA_SEDECO)
            fig.update_layout(yaxis={"categoryorder":"total ascending"}); aplicar_tema_grafica(fig); st.plotly_chart(fig, use_container_width=True)
            explicar_visualizacion("Institución de referencia de cada persona maestra, después de filtros.", "Muestra las 12 instituciones con más personas únicas registradas.", "Una barra mayor indica mayor presencia de personas de esa institución dentro de la base filtrada.")
        with col4:
            carreras_base = maestras_perfil.copy()
            carreras_base["carrera_v"] = _visual(carreras_base["carrera"])
            carreras_base["municipio_v"] = carreras_base["municipio"].apply(normalizar_ubicacion_mexico)

            top_carreras = carreras_base["carrera_v"].value_counts().head(12).index.tolist()
            filas_carrera = []
            for carrera_nombre in top_carreras:
                g = carreras_base[carreras_base["carrera_v"].eq(carrera_nombre)].copy()
                conteos_loc = g["municipio_v"].replace("", "Sin dato").value_counts()
                detalle_municipios = ", ".join(f"{m} ({int(n)})" for m, n in conteos_loc.items())
                filas_carrera.append({
                    "Carrera": carrera_nombre,
                    "Personas": int(len(g)),
                    "Municipios": detalle_municipios or "Sin dato",
                })
            carreras = pd.DataFrame(filas_carrera)
            fig = px.bar(
                carreras, x="Personas", y="Carrera", orientation="h", text="Personas",
                title="Carreras — personas únicas", color="Personas", color_continuous_scale=ESCALA_SEDECO,
                custom_data=["Municipios"],
            )
            fig.update_traces(hovertemplate="<b>%{y}</b><br>Personas únicas: %{x}<br>Municipios: %{customdata[0]}<extra></extra>")
            fig.update_layout(yaxis={"categoryorder":"total ascending"}); aplicar_tema_grafica(fig); st.plotly_chart(fig, use_container_width=True)
            explicar_visualizacion("Carrera de referencia de cada persona maestra; el detalle municipal se obtiene del municipio normalizado.", "Muestra las carreras con más personas únicas y conserva el desglose territorial en el cursor.", "Barras mayores indican más personas registradas en esa carrera; el detalle municipal ayuda a ubicar dónde se concentra ese perfil.")
