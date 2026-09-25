import pandas as pd
import streamlit as st

from utils.core import cargar_personas_base, cargar_vinculaciones_base, limpiar_personas, limpiar_vinculaciones, obtener_personas_maestras, explicar_visualizacion


def _sin_dato(v):
    if pd.isna(v) or str(v).strip() in ["", "nan", "NaT", "None"]:
        return "Sin dato"
    return str(v)


def consulta_persona():
    st.title("👤 Consulta de Persona")
    st.markdown("Consulta una identidad maestra y revisa **todas sus vinculaciones históricas**. Cada fila histórica cuenta como una vinculación y su estado actual es **Vinculado**.")

    personas = limpiar_personas(cargar_personas_base())
    if personas.empty:
        st.info("No hay personas registradas.")
        return

    maestras = obtener_personas_maestras(personas).sort_values(["nombre", "id_persona_maestro"]).reset_index(drop=True)
    buscar = st.text_input("Buscar por nombre o ID maestro", placeholder="Ej. María López o PER-0042")
    vista = maestras.copy()
    if buscar.strip():
        q = buscar.strip().lower()
        vista = vista[vista["nombre"].astype(str).str.lower().str.contains(q, na=False) | vista["id_persona_maestro"].astype(str).str.lower().str.contains(q, na=False)]
    if vista.empty:
        st.warning("No se encontraron coincidencias.")
        return

    opciones = list(vista.index)
    idx = st.selectbox("Persona", opciones, format_func=lambda i: f"{vista.loc[i,'nombre']} — {vista.loc[i,'id_persona_maestro']} — {int(vista.loc[i,'total_vinculaciones'])} vinculaciones")
    p = vista.loc[idx]
    mid = p["id_persona_maestro"]
    hist = personas[personas["id_persona_maestro"].eq(mid)].copy().sort_values(["fecha_registro", "id_persona"], na_position="last")

    st.subheader(_sin_dato(p.get("nombre")))
    st.caption(f"ID persona maestro: {mid}")
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Vinculaciones", len(hist))
    c2.metric("Estado", "Vinculado")
    c3.metric("Tipos", hist["vinculacion"].replace("", pd.NA).nunique())
    fechas = pd.to_datetime(hist["fecha_registro"], errors="coerce").dropna()
    c4.metric("Primera fecha", fechas.min().strftime("%d/%m/%Y") if len(fechas) else "Sin dato")
    c5.metric("Última fecha", fechas.max().strftime("%d/%m/%Y") if len(fechas) else "Sin dato")
    explicar_visualizacion("Historial de la persona seleccionada en la base de personas.", "Resume sus vinculaciones históricas, tipos y rango de fechas.", "Las fechas delimitan el historial disponible y la cantidad de vinculaciones indica recurrencia de registros, no necesariamente contrataciones distintas.")

    st.markdown("### Datos de la persona")
    datos = [("Sexo",p.get("sexo")),("Edad",p.get("edad")),("Municipio",p.get("municipio")),("Institución",p.get("Institución")),("Carrera",p.get("carrera")),("Teléfono",p.get("telefono")),("Correo",p.get("correo"))]
    cols=st.columns(4)
    for n,(k,v) in enumerate(datos): cols[n%4].markdown(f"**{k}:** {_sin_dato(v)}")

    st.markdown("### Historial de vinculaciones")
    tabla = hist[["id_persona","vinculacion","fecha_registro","Año","Institución","carrera","municipio"]].copy()
    tabla["fecha_registro"] = pd.to_datetime(tabla["fecha_registro"], errors="coerce").dt.strftime("%d/%m/%Y").fillna("Sin dato")
    for col in ["vinculacion","Año","Institución","carrera","municipio"]:
        tabla[col] = tabla[col].apply(_sin_dato)
    tabla.insert(2,"Estatus","Vinculado")
    tabla = tabla.rename(columns={"id_persona":"ID vinculación","vinculacion":"Tipo","fecha_registro":"Fecha"})
    st.dataframe(tabla, use_container_width=True, hide_index=True)

    st.markdown("### Seguimiento empresarial")
    seg = limpiar_vinculaciones(cargar_vinculaciones_base())
    seg = seg[seg["id_persona_maestro"].eq(mid)].copy()
    if seg.empty:
        st.info("Vinculado. Empresa, vacante y fechas empresariales: Sin dato.")
    else:
        columnas = [
            "id_vinculacion", "empresa", "sector_empresa", "tipo_vacante", "area_oportunidad",
            "estatus", "fecha_vinculacion", "observaciones", "responsable"
        ]
        columnas = [c for c in columnas if c in seg.columns]
        seg = seg[columnas].copy()
        for col in columnas:
            if col == "fecha_vinculacion":
                seg[col] = pd.to_datetime(seg[col], errors="coerce").dt.strftime("%d/%m/%Y").fillna("Sin dato")
            elif col not in ["id_vinculacion", "estatus"]:
                seg[col] = seg[col].apply(_sin_dato)
        st.dataframe(seg, use_container_width=True, hide_index=True)
