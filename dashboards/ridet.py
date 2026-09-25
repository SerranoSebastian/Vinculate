import base64
from pathlib import Path

import pandas as pd
import streamlit as st

from utils.core import cargar_vacantes_base, explicar_visualizacion

ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
RIDET_IMG_DIR = ASSETS_DIR / "ridet"
RIDET_DOC_DIR = ASSETS_DIR / "documentos"
RIDET_PDF = RIDET_DOC_DIR / "RIDET.pdf"

IMAGENES_GENERALES = [
    "01_portada.png",
    "02_descripcion.png",
    "03_regiones.png",
]

IMAGENES_REGION = {
    "Región Norte": ["04_norte.png"],
    "Región Oriente": ["05_oriente.png"],
    "Región Poniente": ["06_poniente.png"],
    "Región Centro-Norte": ["07_centro_norte_1.png", "08_centro_norte_2.png"],
    "Región Centro-Sur": ["09_centro_sur_1.png", "10_centro_sur_2.png"],
    "Región Sur": ["11_sur_1.png", "12_sur_2.png"],
}

RESUMEN_REGIONES = pd.DataFrame([
    {"Región": "Región Norte", "Cabecera": "Tlaxco", "Municipios": 4, "Sectores": 9, "Empresas": 20, "Instituciones EMS": 12},
    {"Región": "Región Oriente", "Cabecera": "Huamantla", "Municipios": 7, "Sectores": 8, "Empresas": 39, "Instituciones EMS": 17},
    {"Región": "Región Poniente", "Cabecera": "Calpulalpan", "Municipios": 6, "Sectores": 7, "Empresas": 13, "Instituciones EMS": 10},
    {"Región": "Región Centro-Norte", "Cabecera": "Apizaco", "Municipios": 10, "Sectores": 12, "Empresas": 75, "Instituciones EMS": 17},
    {"Región": "Región Centro-Sur", "Cabecera": "Tlaxcala", "Municipios": 12, "Sectores": 9, "Empresas": 82, "Instituciones EMS": 23},
    {"Región": "Región Sur", "Cabecera": "Zacatelco", "Municipios": 20, "Sectores": 11, "Empresas": 78, "Instituciones EMS": 24},
])

# Catálogo inicial para relacionar empresas presentes en la base de vacantes con RIDET.
# Se puede ampliar sin modificar la lógica del módulo.
EMPRESA_REGION = {
    "SUKARNE": "Región Norte",
    "KIMBERLY-CLARK": "Región Norte",
    "EAGLE": "Región Norte",
    "BURY": "Región Oriente",
    "GONAC": "Región Oriente",
    "COMERCIALIZADORA GONAC": "Región Oriente",
    "SONAVOX": "Región Oriente",
    "DRISCOLL'S": "Región Oriente",
    "DRISCOLLS": "Región Oriente",
    "LEAR CORPORATION - HUAMANTLA": "Región Oriente",
    "LOHR": "Región Poniente",
    "ARCOMEX - NANACAMILPA": "Región Poniente",
    "GREENBRIER": "Región Centro-Norte",
    "FETSA": "Región Centro-Norte",
    "SIMEC": "Región Centro-Norte",
    "ACEROS ESPECIALES SIMEC": "Región Centro-Norte",
    "NOVACERAMIC": "Región Centro-Norte",
    "EUWE EUGEN WEXLER": "Región Centro-Norte",
    "EUWE EUGEN WEXLER DE MÉXICO": "Región Centro-Norte",
    "COCA COLA FEMSA": "Región Centro-Norte",
    "COCA-COLA FEMSA": "Región Centro-Norte",
    "MORPHOPLAST": "Región Centro-Norte",
    "VETROTEX": "Región Centro-Norte",
    "SAINT-GOBAIN, PLANTA VETROTEX": "Región Centro-Norte",
    "SALAVERRY": "Región Centro-Sur",
    "GRUPO EMPRESARIAL SALAVERRY": "Región Centro-Sur",
    "PROVIDENCIA": "Región Centro-Sur",
    "GRUPO TEXTIL PROVIDENCIA": "Región Centro-Sur",
    "ALPHA CERÁMICA": "Región Sur",
    "SCHNEIDER ELECTRIC": "Región Sur",
    "BEKAERT": "Región Sur",
    "POLITEL": "Región Sur",
    "TAURUS": "Región Sur",
    "ITISA": "Región Sur",
    "LEAR CORPORATION - PLANTA PAPALOTLA": "Región Sur",
    "SE BORDNETZE": "Región Sur",
    "SEBNMX": "Región Sur",
}


def _normalizar_empresa(valor):
    return str(valor).strip().upper()


def _clasificar_region_empresa(empresa):
    nombre = _normalizar_empresa(empresa)
    if nombre in EMPRESA_REGION:
        return EMPRESA_REGION[nombre]
    for clave, region in EMPRESA_REGION.items():
        if clave in nombre or nombre in clave:
            return region
    return "Sin región asignada"


def _mostrar_imagen(nombre, caption=None):
    ruta = RIDET_IMG_DIR / nombre
    if ruta.exists():
        st.image(str(ruta), caption=caption or nombre, use_container_width=True)
        return True
    st.warning(f"Falta la imagen: assets/ridet/{nombre}")
    return False


def _visor_imagenes(nombres, prefijo_key):
    disponibles = [nombre for nombre in nombres if (RIDET_IMG_DIR / nombre).exists()]
    faltantes = [nombre for nombre in nombres if nombre not in disponibles]

    if faltantes:
        st.info("Coloca las imágenes faltantes en `assets/ridet/` con los nombres indicados al final de esta pantalla.")

    if not disponibles:
        for nombre in nombres:
            _mostrar_imagen(nombre)
        return

    indice_key = f"{prefijo_key}_indice"
    if indice_key not in st.session_state:
        st.session_state[indice_key] = 0
    st.session_state[indice_key] = min(st.session_state[indice_key], len(disponibles) - 1)

    if len(disponibles) > 1:
        anterior, centro, siguiente = st.columns([1, 5, 1])
        with anterior:
            if st.button("◀ Anterior", key=f"{prefijo_key}_anterior"):
                st.session_state[indice_key] = (st.session_state[indice_key] - 1) % len(disponibles)
        with siguiente:
            if st.button("Siguiente ▶", key=f"{prefijo_key}_siguiente"):
                st.session_state[indice_key] = (st.session_state[indice_key] + 1) % len(disponibles)
        with centro:
            actual = disponibles[st.session_state[indice_key]]
            _mostrar_imagen(actual, f"Imagen {st.session_state[indice_key] + 1} de {len(disponibles)}")
    else:
        _mostrar_imagen(disponibles[0])


def _vacantes_con_region():
    df = cargar_vacantes_base().copy()
    if df.empty or "Empresa" not in df.columns:
        return df
    df["Región RIDET"] = df["Empresa"].apply(_clasificar_region_empresa)
    return df


def _mostrar_pdf():
    if not RIDET_PDF.exists():
        st.warning("No se encontró `assets/documentos/RIDET.pdf`.")
        return
    pdf_bytes = RIDET_PDF.read_bytes()
    st.download_button(
        "⬇️ Descargar documento oficial RIDET",
        data=pdf_bytes,
        file_name="RIDET.pdf",
        mime="application/pdf",
    )
    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{pdf_b64}" width="100%" height="850" type="application/pdf"></iframe>',
        unsafe_allow_html=True,
    )


def modulo_ridet():
    RIDET_IMG_DIR.mkdir(parents=True, exist_ok=True)
    RIDET_DOC_DIR.mkdir(parents=True, exist_ok=True)

    st.title("🧭 Regiones Integrales para el Desarrollo Dual de Tlaxcala — RIDET")
    st.markdown(
        "Consulta visualmente las seis regiones económicas, sus empresas, municipios, sectores e instituciones. "
        "Este módulo sustituye al mapa general para evitar que la información se amontone."
    )

    vista = st.radio(
        "Vista RIDET",
        ["🏠 Información general", "🗂️ Regiones", "🏭 Empresas y vacantes", "📊 Estadísticas", "📄 Documento oficial"],
        horizontal=True,
        key="ridet_vista",
        label_visibility="collapsed",
    )

    if vista == "🏠 Información general":
        st.subheader("Presentación del proyecto RIDET")
        _visor_imagenes(IMAGENES_GENERALES, "ridet_general")
        st.divider()
        st.dataframe(RESUMEN_REGIONES, use_container_width=True, hide_index=True)

    if vista == "🗂️ Regiones":
        region = st.selectbox("Selecciona una región", list(IMAGENES_REGION.keys()), key="ridet_region")
        fila = RESUMEN_REGIONES[RESUMEN_REGIONES["Región"] == region].iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Municipios", int(fila["Municipios"]))
        c2.metric("Empresas", int(fila["Empresas"]))
        c3.metric("Sectores", int(fila["Sectores"]))
        c4.metric("Instituciones EMS", int(fila["Instituciones EMS"]))
        explicar_visualizacion("Resumen institucional RIDET incorporado al módulo.", "Muestra municipios, empresas, sectores e instituciones de educación media superior reportados para la región seleccionada.", "Sirve para dimensionar la estructura territorial de la región; son cifras del resumen RIDET, no cálculos derivados de la base de vacantes.")
        st.caption(f"Cabecera regional: {fila['Cabecera']}")
        _visor_imagenes(IMAGENES_REGION[region], f"ridet_{region}")

    if vista == "🏭 Empresas y vacantes":
        st.subheader("Empresas y vacantes clasificadas por región")
        df = _vacantes_con_region()
        if df.empty:
            st.info("No hay registros disponibles en la base de vacantes.")
        else:
            regiones = ["Todas"] + sorted(df["Región RIDET"].dropna().unique().tolist())
            region_filtro = st.selectbox("Región", regiones, key="ridet_empresa_region")
            empresas = ["Todas"] + sorted(df["Empresa"].dropna().astype(str).unique().tolist())
            empresa_filtro = st.selectbox("Empresa", empresas, key="ridet_empresa_nombre")
            df_f = df.copy()
            if region_filtro != "Todas":
                df_f = df_f[df_f["Región RIDET"] == region_filtro]
            if empresa_filtro != "Todas":
                df_f = df_f[df_f["Empresa"] == empresa_filtro]

            c1, c2, c3 = st.columns(3)
            c1.metric("Vacantes", len(df_f))
            c2.metric("Empresas", df_f["Empresa"].nunique())
            c3.metric("Tipos de vacante", df_f["Tipo de Vacante"].nunique() if "Tipo de Vacante" in df_f.columns else 0)
            explicar_visualizacion("Base actual de vacantes clasificada mediante el catálogo de empresas por región RIDET.", "Resume vacantes, empresas y tipos de puesto dentro de los filtros regionales y empresariales.", "Los valores describen registros de la base que pudieron asignarse territorialmente; no equivalen al total de empleo de la región.")
            st.dataframe(df_f, use_container_width=True, height=450)
            st.download_button(
                "⬇️ Descargar resultado",
                df_f.to_csv(index=False).encode("utf-8-sig"),
                "vacantes_por_region_ridet.csv",
                "text/csv",
            )
            sin_region = df[df["Región RIDET"] == "Sin región asignada"]["Empresa"].dropna().unique()
            if len(sin_region):
                with st.expander(f"⚠️ Empresas pendientes de asignar a una región ({len(sin_region)})"):
                    st.dataframe(pd.DataFrame({"Empresa": sorted(sin_region)}), use_container_width=True, hide_index=True)

    if vista == "📊 Estadísticas":
        st.subheader("Indicadores territoriales RIDET")
        total_municipios = int(RESUMEN_REGIONES["Municipios"].sum())
        total_empresas = int(RESUMEN_REGIONES["Empresas"].sum())
        total_instituciones = int(RESUMEN_REGIONES["Instituciones EMS"].sum())
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Regiones", len(RESUMEN_REGIONES))
        c2.metric("Municipios reportados", total_municipios)
        c3.metric("Empresas reportadas", total_empresas)
        c4.metric("Instituciones EMS", total_instituciones)
        explicar_visualizacion("Tabla RESUMEN_REGIONES construida con la información institucional RIDET incluida en el sistema.", "Suma y resume regiones, municipios, empresas e instituciones EMS reportadas.", "Permite comparar escala territorial entre regiones; estas cifras deben leerse como inventario RIDET incorporado, no como conteos de la base de vacantes.")

        st.bar_chart(RESUMEN_REGIONES.set_index("Región")[["Empresas"]])
        explicar_visualizacion("Columna 'Empresas' de RESUMEN_REGIONES RIDET.", "Compara el número de empresas reportadas en cada región.", "Una barra mayor indica una mayor cantidad de empresas reportadas por RIDET en esa región.")
        st.dataframe(RESUMEN_REGIONES, use_container_width=True, hide_index=True)

        df = _vacantes_con_region()
        if not df.empty:
            st.subheader("Vacantes de la base actual por región asignada")
            conteo = df["Región RIDET"].value_counts().rename_axis("Región").reset_index(name="Vacantes")
            st.bar_chart(conteo.set_index("Región"))
            explicar_visualizacion("Base actual de vacantes después de asignar cada empresa a una región RIDET.", "Cuenta registros de vacantes por región asignada.", "Regiones con barras mayores concentran más publicaciones registradas en la base actual; 'Sin región asignada' señala empresas pendientes de clasificación.")
            st.dataframe(conteo, use_container_width=True, hide_index=True)

    if vista == "📄 Documento oficial":
        st.subheader("Documento oficial RIDET")
        st.caption("El PDF se conserva como fuente institucional; las imágenes permiten una consulta más rápida por región.")
        _mostrar_pdf()

    with st.expander("📁 Nombres y carpeta exacta para las 12 imágenes"):
        st.code(
            "assets/ridet/\n"
            "├── 01_portada.png\n"
            "├── 02_descripcion.png\n"
            "├── 03_regiones.png\n"
            "├── 04_norte.png\n"
            "├── 05_oriente.png\n"
            "├── 06_poniente.png\n"
            "├── 07_centro_norte_1.png\n"
            "├── 08_centro_norte_2.png\n"
            "├── 09_centro_sur_1.png\n"
            "├── 10_centro_sur_2.png\n"
            "├── 11_sur_1.png\n"
            "└── 12_sur_2.png"
        )
