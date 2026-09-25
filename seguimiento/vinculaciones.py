from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from config.estilos import ESCALA_SEDECO, aplicar_tema_grafica
from utils.catalogos_vacantes import (
    AREAS_OPORTUNIDAD,
    EMPRESAS_CATALOGO,
    EMPRESAS_SECTOR,
    PUESTOS_CATALOGO,
)
from utils.core import *


ESTATUS_SEGUIMIENTO = ["Vinculado", "Colocado", "No vinculado"]
ESTATUS_NUEVO = ["Vinculado", "No vinculado"]


def _normalizar_fecha(valor):
    if valor in [None, ""]:
        return ""
    try:
        return pd.to_datetime(valor).strftime("%Y-%m-%d")
    except Exception:
        return ""


def _crear_id_vinculacion(df):
    return f"VIN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(df)+1}"


def _indice_opcion(opciones, valor, default=0):
    try:
        return opciones.index(valor)
    except ValueError:
        return default


def _opciones_con_legacy(catalogo, valor_actual, especiales=()):
    opciones = list(dict.fromkeys([*especiales, *catalogo]))
    valor = str(valor_actual or "").strip()
    if valor and valor not in opciones and valor not in {"Sin asignar", "nan", "None"}:
        opciones.append(valor)
    return opciones


@st.cache_data(show_spinner=False)
def _personas_estado(personas, seguimientos):
    maestras = obtener_personas_maestras(personas).copy()
    seg = limpiar_vinculaciones(seguimientos)
    if maestras.empty:
        return maestras
    filas = []
    for _, p in maestras.iterrows():
        mid = p["id_persona_maestro"]
        g = seg[seg["id_persona_maestro"].eq(mid)].copy()
        r = p.to_dict()
        if g.empty:
            # El registro histórico existe y cuenta como vinculación; todavía puede no tener seguimiento empresarial.
            r.update({"estatus_general": "Vinculado", "seguimientos_empresa": 0, "empresas_contactadas": 0, "empresa_actual": ""})
        else:
            g = g.sort_values(["fecha_actualizacion", "fecha_vinculacion"], na_position="first")
            coloc = g[g["estatus"].eq("Colocado")].copy()
            if not coloc.empty:
                coloc = coloc.sort_values(["fecha_colocacion", "fecha_actualizacion"], na_position="first")
                ult = coloc.iloc[-1]
                estatus_general = "Colocado"
            else:
                ult = g.iloc[-1]
                estatus_general = ult["estatus"]
            r.update({
                "estatus_general": estatus_general,
                "seguimientos_empresa": len(g),
                "empresas_contactadas": g.loc[g["empresa"].ne("Sin asignar"), "empresa"].nunique(),
                "empresa_actual": "" if ult["empresa"] == "Sin asignar" else ult["empresa"],
            })
        filas.append(r)
    return pd.DataFrame(filas)


def _kpis(personas_estado, seguimientos):
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("👤 Personas únicas", len(personas_estado))
    c2.metric("🔗 Vinculaciones históricas", int(personas_estado["total_vinculaciones"].sum()) if not personas_estado.empty else 0)
    c3.metric("🔗 Vinculados", int(personas_estado["estatus_general"].eq("Vinculado").sum()) if not personas_estado.empty else 0)
    c4.metric("✅ Colocados", int(personas_estado["estatus_general"].eq("Colocado").sum()) if not personas_estado.empty else 0)
    c5.metric("⭕ No vinculados", int(personas_estado["estatus_general"].eq("No vinculado").sum()) if not personas_estado.empty else 0)
    c6.metric("🧾 Seguimientos", len(seguimientos))
    empresas = seguimientos.loc[seguimientos["empresa"].ne("Sin asignar"), "empresa"].nunique() if not seguimientos.empty else 0
    c7.metric("🏢 Empresas", int(empresas))
    explicar_visualizacion(
        "Base maestra de personas y archivo de seguimientos data/vinculaciones.csv.",
        "Resume personas únicas, vinculaciones históricas, estatus actual, cantidad de seguimientos y empresas con seguimiento.",
        "Las vinculaciones históricas provienen de registros de persona; el estatus actual se toma del seguimiento más reciente cuando existe. Seguimientos y empresas miden actividad operativa, no contrataciones por sí solos."
    )


def _selector_empresa_y_puesto(mid, vacantes):
    vacantes = limpiar_vacantes(vacantes)
    activas = vacantes[vacantes["Estado"].eq("Activa")].reset_index(drop=True)
    modo = st.radio(
        "Empresa / puesto",
        ["Seleccionar de catálogos", "Elegir vacante activa"],
        horizontal=True,
        key=f"seg_modo_{mid}",
    )

    if modo == "Elegir vacante activa" and not activas.empty:
        vi = st.selectbox(
            "Vacante activa",
            list(activas.index),
            format_func=lambda i: f"{activas.loc[i, 'Empresa']} — {activas.loc[i, 'Tipo de Vacante']}",
            key=f"seg_vac_{mid}",
        )
        fila = activas.loc[vi]
        empresa = str(fila["Empresa"])
        puesto = str(fila["Tipo de Vacante"])
        sector = str(fila.get("Sector Empresa", "")) or EMPRESAS_SECTOR.get(empresa, "Sin dato")
        area = str(fila.get("Área de Oportunidad", "")) or "Otro / Sin dato"
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Empresa", value=empresa, disabled=True, key=f"seg_emp_show_{mid}")
            st.text_input("Sector", value=sector or "Sin dato", disabled=True, key=f"seg_sector_show_{mid}")
        with c2:
            st.text_input("Vacante / puesto", value=puesto, disabled=True, key=f"seg_puesto_show_{mid}")
            st.text_input("Área de oportunidad", value=area or "Otro / Sin dato", disabled=True, key=f"seg_area_show_{mid}")
        return empresa, puesto, sector, area

    if modo == "Elegir vacante activa" and activas.empty:
        st.warning("No hay vacantes activas. Puedes seleccionar empresa y puesto desde los catálogos.")

    c1, c2 = st.columns(2)
    with c1:
        empresa = st.selectbox("Empresa", EMPRESAS_CATALOGO, key=f"seg_emp_{mid}")
        sector = EMPRESAS_SECTOR.get(empresa, "Sin dato")
        st.text_input("Sector", value=sector, disabled=True, key=f"seg_sector_{mid}")
    with c2:
        puesto = st.selectbox("Vacante / puesto", PUESTOS_CATALOGO, key=f"seg_puesto_{mid}")
        area = st.selectbox("Área de oportunidad", AREAS_OPORTUNIDAD, key=f"seg_area_{mid}")
    return empresa, puesto, sector, area


def _agregar(personas, vacantes, seguimientos):
    st.subheader("➕ Nuevo seguimiento persona → empresa")
    maestras = obtener_personas_maestras(personas).sort_values(["nombre", "id_persona_maestro"]).reset_index(drop=True)
    if maestras.empty:
        st.info("No hay personas registradas.")
        return

    # Solo estos dos controles quedan fuera del formulario porque cambian qué opciones se muestran.
    # El resto no provoca reruns mientras se captura: Streamlit procesa todo hasta pulsar Guardar.
    idx = st.selectbox(
        "Persona",
        list(maestras.index),
        format_func=lambda i: f"{maestras.loc[i, 'nombre']} — {maestras.loc[i, 'id_persona_maestro']} — {int(maestras.loc[i, 'total_vinculaciones'])} vinculaciones históricas",
        key="seg_persona_nueva",
    )
    persona = maestras.loc[idx]
    mid = persona["id_persona_maestro"]
    modo = st.radio(
        "Empresa / puesto",
        ["Seleccionar de catálogos", "Elegir vacante activa"],
        horizontal=True,
        key="seg_modo_nuevo",
    )

    historicos = limpiar_personas(personas)
    hist = historicos[historicos["id_persona_maestro"].eq(mid)].copy()
    opciones_origen = [""] + hist["id_persona"].tolist()
    vacantes_limpias = limpiar_vacantes(vacantes)
    activas = vacantes_limpias[vacantes_limpias["Estado"].eq("Activa")].reset_index(drop=True)

    with st.form("seg_nuevo_form", clear_on_submit=False):
        origen = st.selectbox(
            "Vinculación histórica de origen (opcional)",
            opciones_origen,
            format_func=lambda x: "Sin asociación específica" if x == "" else f"{x} — {hist.loc[hist['id_persona'].eq(x), 'vinculacion'].iloc[0]}",
        )

        if modo == "Elegir vacante activa" and not activas.empty:
            vi = st.selectbox(
                "Vacante activa",
                list(activas.index),
                format_func=lambda i: f"{activas.loc[i, 'Empresa']} — {activas.loc[i, 'Tipo de Vacante']}",
            )
            fila_v = activas.loc[vi]
            empresa = str(fila_v["Empresa"])
            puesto = str(fila_v["Tipo de Vacante"])
            sector = str(fila_v.get("Sector Empresa", "")) or EMPRESAS_SECTOR.get(empresa, "Sin dato")
            area = str(fila_v.get("Área de Oportunidad", "")) or "Otro / Sin dato"
            st.caption(f"🏢 {empresa} · {sector} · {puesto} · {area}")
        else:
            if modo == "Elegir vacante activa" and activas.empty:
                st.info("No hay vacantes activas; usa los catálogos normalizados.")
            c1, c2 = st.columns(2)
            with c1:
                empresa = st.selectbox("Empresa", EMPRESAS_CATALOGO)
                puesto = st.selectbox("Vacante / puesto", PUESTOS_CATALOGO)
            with c2:
                area = st.selectbox("Área de oportunidad", AREAS_OPORTUNIDAD)
                st.caption("El sector se asigna automáticamente al guardar según la empresa seleccionada.")
            sector = EMPRESAS_SECTOR.get(empresa, "Sin dato")

        c1, c2 = st.columns(2)
        with c1:
            estatus = st.selectbox("Estatus", ESTATUS_NUEVO)
            responsable = st.text_input("Responsable", value="SEDECO")
        with c2:
            vinc = st.date_input(
                "Fecha de vinculación",
                value=datetime.today().date(),
                help="Si el estatus es No vinculado y no existe una fecha de vinculación real, deja la fecha sin dato después desde edición.",
            )
            obs = st.text_area("Observaciones")
        guardar = st.form_submit_button("💾 Guardar seguimiento", use_container_width=True)

    if guardar:
        fecha_final = _normalizar_fecha(vinc) if estatus == "Vinculado" else ""
        nuevo = pd.DataFrame([{
            "id_vinculacion": _crear_id_vinculacion(seguimientos),
            "id_persona_maestro": mid,
            "id_registro_origen": origen,
            "nombre_persona": persona["nombre"],
            "empresa": empresa,
            "sector_empresa": sector,
            "tipo_vacante": puesto,
            "area_oportunidad": area,
            "estatus": estatus,
            "fecha_vinculacion": fecha_final,
            "fecha_colocacion": "",
            "observaciones": obs,
            "responsable": responsable,
            "fecha_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }])
        res = guardar_vinculaciones_base(
            pd.concat([seguimientos, nuevo], ignore_index=True),
            usuario=responsable,
            accion="alta seguimiento",
        )
        st.session_state["seg_mensaje_guardado"] = f"✅ Seguimiento guardado correctamente para {persona['nombre']}. Total de seguimientos: {res['total']}."
        st.rerun()

def _editar(seguimientos):
    st.subheader("✏️ Editar / eliminar seguimiento")
    df = limpiar_vinculaciones(seguimientos).reset_index(drop=True)
    if df.empty:
        st.info("No hay seguimientos.")
        return

    idx = st.selectbox(
        "Seguimiento",
        list(df.index),
        format_func=lambda i: f"{df.loc[i, 'nombre_persona']} | {df.loc[i, 'empresa']} | {df.loc[i, 'estatus']} | {df.loc[i, 'id_vinculacion']}",
        key="seg_edit_sel",
    )
    f = df.loc[idx]
    key = f["id_vinculacion"]

    empresas = _opciones_con_legacy(EMPRESAS_CATALOGO, f["empresa"])
    puestos = _opciones_con_legacy(PUESTOS_CATALOGO, f["tipo_vacante"])
    areas = _opciones_con_legacy(AREAS_OPORTUNIDAD, f.get("area_oportunidad", ""), especiales=("Otro / Sin dato",))

    with st.form("seg_editar_form"):
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("ID seguimiento", value=str(f["id_vinculacion"]), disabled=True)
            st.text_input("ID persona maestra", value=str(f["id_persona_maestro"]), disabled=True)
            empresa = st.selectbox("Empresa", empresas, index=_indice_opcion(empresas, str(f["empresa"])))
            sector = EMPRESAS_SECTOR.get(empresa, str(f.get("sector_empresa", "")) or "Sin dato")
            st.text_input("Sector", value=sector, disabled=True)
            puesto = st.selectbox("Vacante / puesto", puestos, index=_indice_opcion(puestos, str(f["tipo_vacante"])))
            area_actual = str(f.get("area_oportunidad", "")) or "Otro / Sin dato"
            area = st.selectbox("Área de oportunidad", areas, index=_indice_opcion(areas, area_actual))
        with c2:
            estatus_actual = str(f["estatus"])
            estatus = st.selectbox("Estatus", ESTATUS_SEGUIMIENTO, index=_indice_opcion(ESTATUS_SEGUIMIENTO, estatus_actual))
            fv = pd.to_datetime(f["fecha_vinculacion"], errors="coerce")
            vinc = st.date_input("Fecha de vinculación", value=None if pd.isna(fv) else fv.date())
            fc = pd.to_datetime(f.get("fecha_colocacion"), errors="coerce")
            coloc = st.date_input("Fecha de colocación", value=(datetime.today().date() if estatus == "Colocado" and pd.isna(fc) else (None if pd.isna(fc) else fc.date())), disabled=estatus != "Colocado")
            obs = st.text_area("Observaciones", value=str(f["observaciones"]))
            resp = st.text_input("Responsable", value=str(f["responsable"]))
        guardar = st.form_submit_button("💾 Guardar cambios", use_container_width=True)

    eliminar = st.button("🗑️ Eliminar seguimiento", key=f"seg_del_{key}")
    if guardar:
        df.loc[idx, [
            "empresa", "sector_empresa", "tipo_vacante", "area_oportunidad", "estatus",
            "fecha_vinculacion", "fecha_colocacion", "observaciones", "responsable", "fecha_actualizacion",
        ]] = [
            empresa, sector, puesto, area, estatus,
            _normalizar_fecha(vinc), _normalizar_fecha(coloc) if estatus == "Colocado" else "", obs, resp, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ]
        guardar_registro_editado("vinculaciones", df.loc[[idx], VINCULACIONES_COLS], usuario=resp, accion="edición seguimiento")
        st.session_state["seg_mensaje_guardado"] = "✅ Seguimiento actualizado correctamente."
        st.rerun()
    if eliminar:
        eliminar_registro("vinculaciones", key, usuario="SEDECO", accion="eliminación seguimiento")
        st.session_state["seg_mensaje_guardado"] = "✅ Seguimiento eliminado correctamente."
        st.rerun()


def _estadisticas(personas, estado, seguimientos):
    st.subheader("📊 Estadísticas de seguimiento")
    if estado.empty:
        st.info("Sin información para mostrar.")
        return

    c1, c2 = st.columns(2)
    with c1:
        e = estado["estatus_general"].value_counts().reset_index()
        e.columns = ["Estatus", "Personas"]
        fig = px.pie(e, names="Estatus", values="Personas", hole=.5, title="Estatus actual por persona")
        aplicar_tema_grafica(fig)
        st.plotly_chart(fig, use_container_width=True)
        explicar_visualizacion("Estatus general calculado por persona a partir de sus seguimientos.", "Distribuye personas según su estatus actual.", "Una porción mayor muestra qué estatus concentra más personas; debe interpretarse con la regla del seguimiento más reciente.")
    with c2:
        hist = personas.groupby("id_persona_maestro").size().value_counts().sort_index().reset_index()
        hist.columns = ["Vinculaciones", "Personas"]
        fig = px.bar(
            hist,
            x="Vinculaciones",
            y="Personas",
            text="Personas",
            title="Vinculaciones históricas por persona",
            color="Personas",
            color_continuous_scale=ESCALA_SEDECO,
        )
        aplicar_tema_grafica(fig)
        st.plotly_chart(fig, use_container_width=True)
        explicar_visualizacion("Base histórica de personas agrupada por ID maestro.", "Muestra cuántas personas tienen 1, 2, 3 o más vinculaciones históricas.", "Permite medir recurrencia: barras en cantidades mayores a 1 representan personas que aparecen en múltiples vinculaciones.")

    seg = limpiar_vinculaciones(seguimientos)
    if not seg.empty:
        seg_validas = seg.copy()
        seg_validas["Año"] = seg_validas["fecha_vinculacion"].dt.year.astype("Int64")
        anuales = seg_validas.dropna(subset=["Año"]).groupby(["Año", "estatus"]).size().reset_index(name="Seguimientos")
        if not anuales.empty:
            fig = px.bar(
                anuales,
                x="Año",
                y="Seguimientos",
                color="estatus",
                barmode="group",
                text="Seguimientos",
                title="Seguimientos por año y estatus",
            )
            aplicar_tema_grafica(fig)
            st.plotly_chart(fig, use_container_width=True)
            explicar_visualizacion("Fecha de vinculación y estatus de cada seguimiento empresarial.", "Cuenta seguimientos por año y estatus.", "Permite comparar la actividad de seguimiento y sus resultados entre años; registros sin fecha no se incluyen en esta gráfica.")

        c3, c4 = st.columns(2)
        with c3:
            emp = seg_validas[seg_validas["empresa"].ne("Sin asignar")]["empresa"].value_counts().reset_index()
            emp.columns = ["Empresa", "Seguimientos"]
            if not emp.empty:
                fig = px.bar(emp, y="Empresa", x="Seguimientos", orientation="h", text="Seguimientos", title="Seguimientos por empresa")
                aplicar_tema_grafica(fig)
                fig.update_layout(height=max(420, 25 * len(emp) + 160), yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig, use_container_width=True)
                explicar_visualizacion("Campo 'empresa' de los seguimientos, excluyendo 'Sin asignar'.", "Cuenta seguimientos registrados para cada empresa.", "Empresas con barras mayores concentran más acciones de seguimiento dentro de la base, no necesariamente más vinculaciones exitosas.")
        with c4:
            puestos = seg_validas[seg_validas["tipo_vacante"].ne("Sin asignar")]["tipo_vacante"].value_counts().reset_index()
            puestos.columns = ["Puesto", "Seguimientos"]
            if not puestos.empty:
                fig = px.bar(puestos, y="Puesto", x="Seguimientos", orientation="h", text="Seguimientos", title="Seguimientos por puesto")
                aplicar_tema_grafica(fig)
                fig.update_layout(height=max(420, 25 * len(puestos) + 160), yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig, use_container_width=True)
                explicar_visualizacion("Campo 'tipo_vacante' de los seguimientos, excluyendo 'Sin asignar'.", "Cuenta seguimientos asociados a cada puesto.", "Los puestos con mayor valor aparecen con más frecuencia en el seguimiento; esto describe la operación registrada, no la demanda total del mercado.")

    st.markdown("### Colocaciones")
    colocados = estado[estado["estatus_general"].eq("Colocado")].copy()
    seg_col = seg[seg["estatus"].eq("Colocado")].copy() if not seg.empty else seg.copy()
    base_vinc = int(estado["estatus_general"].isin(["Vinculado", "Colocado"]).sum())
    total_vinc = max(base_vinc, 1)
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Personas colocadas", len(colocados))
    k2.metric("Registros de colocación", len(seg_col))
    k3.metric("Empresas con colocación", seg_col.loc[seg_col["empresa"].ne("Sin asignar"), "empresa"].nunique() if not seg_col.empty else 0)
    k4.metric("Tasa sobre personas vinculadas", f"{(len(colocados)/total_vinc)*100:.1f}%")
    if not colocados.empty:
        a,b = st.columns(2)
        with a:
            if "sexo" in colocados.columns:
                d=colocados["sexo"].fillna("Sin dato").replace("", "Sin dato").value_counts().reset_index(); d.columns=["Sexo","Personas"]
                fig=px.bar(d,x="Sexo",y="Personas",text="Personas",title="Personas colocadas por sexo"); aplicar_tema_grafica(fig); st.plotly_chart(fig,use_container_width=True)
        with b:
            if "municipio" in colocados.columns:
                d=colocados["municipio"].fillna("Sin dato").replace("", "Sin dato").value_counts().head(15).reset_index(); d.columns=["Municipio","Personas"]
                fig=px.bar(d,y="Municipio",x="Personas",orientation="h",text="Personas",title="Personas colocadas por municipio"); aplicar_tema_grafica(fig); fig.update_layout(yaxis={"categoryorder":"total ascending"}); st.plotly_chart(fig,use_container_width=True)
        if not seg_col.empty:
            d=seg_col[seg_col["empresa"].ne("Sin asignar")]["empresa"].value_counts().head(15).reset_index(); d.columns=["Empresa","Colocaciones"]
            if not d.empty:
                fig=px.bar(d,y="Empresa",x="Colocaciones",orientation="h",text="Colocaciones",title="Colocaciones por empresa"); aplicar_tema_grafica(fig); fig.update_layout(yaxis={"categoryorder":"total ascending"}); st.plotly_chart(fig,use_container_width=True)

    st.dataframe(
        estado[["id_persona_maestro", "nombre", "total_vinculaciones", "estatus_general", "seguimientos_empresa", "empresas_contactadas", "empresa_actual"]],
        use_container_width=True,
        hide_index=True,
    )


def seguimiento_vinculaciones():
    st.title("🔗 Seguimiento de Vinculación")
    st.markdown(
        "Cada persona puede tener **múltiples vinculaciones históricas** y **múltiples seguimientos con empresas**. "
        "Empresa, puesto y área se seleccionan desde los mismos catálogos normalizados del módulo de vacantes."
    )

    mensaje = st.session_state.pop("seg_mensaje_guardado", None)
    if mensaje:
        st.success(mensaje)

    personas = limpiar_personas(cargar_personas_base())
    vacantes = cargar_vacantes_base()
    seguimientos = limpiar_vinculaciones(cargar_vinculaciones_base())
    estado = _personas_estado(personas, seguimientos)
    _kpis(estado, seguimientos)

    vista = st.radio(
        "Apartado",
        ["➕ Nuevo seguimiento", "✏️ Editar / eliminar", "📊 Estadísticas", "👤 Historial persona", "⬇️ Exportar"],
        horizontal=True,
        key="seguimiento_apartado",
        label_visibility="collapsed",
    )
    if vista == "➕ Nuevo seguimiento":
        _agregar(personas, vacantes, seguimientos)
    elif vista == "✏️ Editar / eliminar":
        _editar(seguimientos)
    elif vista == "📊 Estadísticas":
        _estadisticas(personas, estado, seguimientos)
    elif vista == "👤 Historial persona":
        maestras = obtener_personas_maestras(personas).sort_values(["nombre", "id_persona_maestro"]).reset_index(drop=True)
        if maestras.empty:
            st.info("Sin personas.")
        else:
            i = st.selectbox(
                "Persona",
                list(maestras.index),
                format_func=lambda x: f"{maestras.loc[x, 'nombre']} — {maestras.loc[x, 'id_persona_maestro']}",
                key="seg_hist_persona",
            )
            p = maestras.loc[i]
            g = seguimientos[seguimientos["id_persona_maestro"].eq(p["id_persona_maestro"])].copy()
            st.metric("Vinculaciones históricas", int(p["total_vinculaciones"]))
            explicar_visualizacion("Historial de la persona seleccionada en la base de personas.", "Cuenta todas sus vinculaciones históricas conservadas.", "Un valor mayor a 1 significa que la persona tiene múltiples registros de vinculación en el historial.")
            if g.empty:
                st.info("Esta persona todavía no tiene seguimientos empresariales.")
            else:
                g = g.sort_values(["fecha_vinculacion", "fecha_actualizacion"], na_position="last")
                mostrar = g[[
                    "id_vinculacion", "empresa", "sector_empresa", "tipo_vacante", "area_oportunidad",
                    "estatus", "fecha_vinculacion", "fecha_colocacion", "observaciones", "responsable",
                ]].copy()
                mostrar["fecha_vinculacion"] = mostrar["fecha_vinculacion"].apply(
                    lambda x: "Sin dato" if pd.isna(x) else pd.to_datetime(x).strftime("%d/%m/%Y")
                )
                mostrar["fecha_colocacion"] = mostrar["fecha_colocacion"].apply(
                    lambda x: "Sin dato" if pd.isna(x) else pd.to_datetime(x).strftime("%d/%m/%Y")
                )
                st.dataframe(mostrar, use_container_width=True, hide_index=True)
    elif vista == "⬇️ Exportar":
        st.download_button(
            "⬇️ Descargar seguimientos CSV",
            data=seguimientos.to_csv(index=False).encode("utf-8-sig"),
            file_name="seguimientos_vinculacion.csv",
            mime="text/csv",
            use_container_width=True,
        )
