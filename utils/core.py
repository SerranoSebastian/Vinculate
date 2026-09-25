import io
import os
import tempfile
import unicodedata
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.cloud_db import (
    cloud_enabled, ping_cloud, fetch_all as cloud_fetch_all,
    upsert_df as cloud_upsert_df, insert_df as cloud_insert_df,
    delete_ids as cloud_delete_ids, count_rows as cloud_count_rows,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = BASE_DIR / "backups"
DATA_DIR.mkdir(exist_ok=True)
BACKUP_DIR.mkdir(exist_ok=True)

PERSONAS_FILE = DATA_DIR / "Base de datos_Persona.csv"
VACANTES_FILE = DATA_DIR / "vacantes_consolidadas_empresas.csv"
HISTORIAL_FILE = DATA_DIR / "historial_cargas.csv"
VINCULACIONES_FILE = DATA_DIR / "vinculaciones.csv"
VINCULADOS_FILE = DATA_DIR / "personas_vinculadas.csv"
PENDIENTES_FILE = DATA_DIR / "personas_pendientes.csv"
NO_VINCULADOS_FILE = DATA_DIR / "personas_no_vinculadas.csv"

ORIG_PERSONAS = [
    BASE_DIR / "Base de datos_Persona.csv",
    BASE_DIR / "Base de datos_Persona(1).csv",
    BASE_DIR / "Base de datos_Personas.csv",
    BASE_DIR / "Base de datos_Personas(3).csv",
]
ORIG_VACANTES = [
    BASE_DIR / "vacantes_consolidadas_empresas.csv",
    BASE_DIR / "vacantes_consolidadas_empresas(2).csv",
    BASE_DIR / "vacantes_consolidadas_empresas(3).csv",
]

# Una fila de PERSONAS representa una vinculacion historica.
# id_persona = ID del registro/vinculacion historica.
# id_persona_maestro = ID permanente de la persona real.
PERSONAS_COLS = [
    "id_persona", "id_persona_maestro", "nombre", "sexo", "edad", "escolaridad",
    "carrera", "Institución", "id_institucion", "municipio", "id_municipio",
    "telefono", "correo", "grupo_prioritario", "vinculacion", "fecha_registro",
    "Año", "area_carrera", "estatus_vinculacion"
]

VACANTES_COLS = [
    "ID Vacante", "ID Registro Origen", "Actividad", "Fecha", "Empresa", "Sector Empresa",
    "Puesto Original", "Tipo de Vacante", "Categoría de Puesto",
    "Tipo de Oportunidad", "Área de Oportunidad", "Descripción",
    "Requisitos", "Beneficios", "Link de la Publicación", "Estado"
]
ESTADOS_VACANTE = ["Activa", "Inactiva"]
TIPOS_OPORTUNIDAD = ["Empleo", "Prácticas Profesionales", "Servicio Social"]

# Variantes claras que deben resolverse siempre al mismo nombre.
ALIASES_PUESTOS_VACANTES = {
    "ayudante general": "Ayudante General",
    "ayudantes generales": "Ayudante General",
    "auxiliares generales": "Ayudante General",
    "soldador": "Soldador", "soldadores": "Soldador",
    "electromecanico": "Electromecánico", "electromecanicos": "Electromecánico",
    "operadores de costura": "Operador de Costura", "costureros": "Operador de Costura",
    "inspector de calidad": "Inspector de Calidad",
    "supervisor de mantenimiento": "Supervisor de Mantenimiento",
    "tecnico de mantenimiento": "Técnico de Mantenimiento",
    "tecnico en mantenimiento": "Técnico de Mantenimiento",
    "ayudante de produccion": "Ayudante de Producción",
    "mecanico textil": "Mecánico Textil",
    "ingeniero en mantenimiento": "Ingeniero de Mantenimiento",
    "practica profesionales": "Prácticas Profesionales",
    "practicas profesionales": "Prácticas Profesionales",
    "residencia practicas profesionales": "Prácticas Profesionales",
}

HISTORIAL_COLS = [
    "fecha_hora", "usuario", "base", "origen", "archivo_origen",
    "registros_recibidos", "registros_guardados", "duplicados_actualizados", "total_final"
]

# Seguimiento operativo. Puede haber muchos seguimientos para una misma persona maestra.
VINCULACIONES_COLS = [
    "id_vinculacion", "id_persona_maestro", "id_registro_origen", "nombre_persona",
    "empresa", "sector_empresa", "tipo_vacante", "area_oportunidad", "estatus",
    "fecha_vinculacion", "fecha_colocacion", "observaciones", "responsable", "fecha_actualizacion"
]
ESTATUS_VINCULACION = ["Vinculado", "Colocado", "No vinculado"]
TIPOS_VINCULACION = ["Inserción Laboral", "Atención", "Prácticas Profesionales", "Servicio Social"]
PREFIJOS_VINCULACION = {
    "Inserción Laboral": "I",
    "Atención": "A",
    "Prácticas Profesionales": "P",
    "Servicio Social": "S",
}

# Catálogo único de ubicación para evitar variantes de escritura.
# Tlaxcala se captura por municipio; para el resto del país se captura el estado.
MUNICIPIOS_TLAXCALA = [
    "ACUAMANALA DE MIGUEL HIDALGO",
    "ALTZAYANCA",
    "AMAXAC DE GUERRERO",
    "APETATITLÁN DE ANTONIO CARVAJAL",
    "APIZACO",
    "ATLANGATEPEC",
    "BENITO JUÁREZ",
    "CALPULALPAN",
    "CHIAUTEMPAN",
    "CONTLA DE JUAN CUAMATZI",
    "CUAPIAXTLA",
    "CUAXOMULCO",
    "EL CARMEN TEQUEXQUITLA",
    "EMILIANO ZAPATA",
    "ESPAÑITA",
    "HUAMANTLA",
    "HUEYOTLIPAN",
    "IXTACUIXTLA DE MARIANO MATAMOROS",
    "IXTENCO",
    "LA MAGDALENA TLALTELULCO",
    "LÁZARO CÁRDENAS",
    "MAZATECOCHCO DE JOSÉ MARÍA MORELOS",
    "MUÑOZ DE DOMINGO ARENAS",
    "NANACAMILPA DE MARIANO ARISTA",
    "NATIVITAS",
    "PANOTLA",
    "PAPALOTLA DE XICOHTÉNCATL",
    "SAN DAMIÁN TEXOLOC",
    "SAN FRANCISCO TETLANOHCAN",
    "SAN JERÓNIMO ZACUALPAN",
    "SAN JOSÉ TEACALCO",
    "SAN JUAN HUACTZINCO",
    "SAN LORENZO AXOCOMANITLA",
    "SAN LUCAS TECOPILCO",
    "SAN PABLO DEL MONTE",
    "SANCTORUM DE LÁZARO CÁRDENAS",
    "SANTA ANA NOPALUCAN",
    "SANTA APOLONIA TEACALCO",
    "SANTA CATARINA AYOMETLA",
    "SANTA CRUZ QUILEHTLA",
    "SANTA CRUZ TLAXCALA",
    "SANTA ISABEL XILOXOXTLA",
    "TENANCINGO",
    "TEOLOCHOLCO",
    "TEPETITLA DE LARDIZÁBAL",
    "TEPEYANCO",
    "TERRENATE",
    "TETLA DE LA SOLIDARIDAD",
    "TETLATLAHUCA",
    "TLAXCALA",
    "TLAXCO",
    "TOCATLÁN",
    "TOTOLAC",
    "TZOMPANTEPEC",
    "XALOSTOC",
    "XALTOCAN",
    "XICOHTZINCO",
    "YAUHQUEMECAN",
    "ZACATELCO",
    "ZITLALTEPEC DE TRINIDAD SÁNCHEZ SANTOS",
]

ESTADOS_MEXICO_SIN_TLAXCALA = [
    "AGUASCALIENTES", "BAJA CALIFORNIA", "BAJA CALIFORNIA SUR", "CAMPECHE",
    "CHIAPAS", "CHIHUAHUA", "CIUDAD DE MÉXICO", "COAHUILA", "COLIMA", "DURANGO",
    "GUANAJUATO", "GUERRERO", "HIDALGO", "JALISCO", "ESTADO DE MÉXICO",
    "MICHOACÁN", "MORELOS", "NAYARIT", "NUEVO LEÓN", "OAXACA", "PUEBLA",
    "QUERÉTARO", "QUINTANA ROO", "SAN LUIS POTOSÍ", "SINALOA", "SONORA",
    "TABASCO", "TAMAULIPAS", "VERACRUZ", "YUCATÁN", "ZACATECAS",
]

OPCIONES_UBICACION_CAPTURA = [""] + MUNICIPIOS_TLAXCALA + ESTADOS_MEXICO_SIN_TLAXCALA + ["Indefinido"]
OPCIONES_UBICACION_FILTRO = MUNICIPIOS_TLAXCALA + ESTADOS_MEXICO_SIN_TLAXCALA + ["Otro Estado", "Indefinido", "Sin dato"]


def normalizar_ubicacion_mexico(valor):
    """Devuelve una etiqueta canónica sin convertir vacío en Indefinido."""
    if pd.isna(valor) or str(valor).strip() == "":
        return ""
    original = str(valor).strip()
    key = normalizar_texto(original)
    if key == "indefinido":
        return "Indefinido"
    if key == "otro estado":
        return "Otro Estado"

    catalogo = MUNICIPIOS_TLAXCALA + ESTADOS_MEXICO_SIN_TLAXCALA
    mapa = {normalizar_texto(x): x for x in catalogo}
    aliases = {
        "estado de mexico": "ESTADO DE MÉXICO",
        "mexico": "ESTADO DE MÉXICO",
        "cdmx": "CIUDAD DE MÉXICO",
        "ciudad de mexico": "CIUDAD DE MÉXICO",
        "coahuila de zaragoza": "COAHUILA",
        "michoacan de ocampo": "MICHOACÁN",
        "veracruz de ignacio de la llave": "VERACRUZ",
        "sanctórum de lazaro cardenas": "SANCTORUM DE LÁZARO CÁRDENAS",
        "sanctorum de lazaro cardenas": "SANCTORUM DE LÁZARO CÁRDENAS",
        "yauhquemehcan": "YAUHQUEMECAN",
        "xaloztoc": "XALOSTOC",
    }
    if key in aliases:
        return aliases[key]
    return mapa.get(key, original)


def opciones_ubicacion(valor_actual="", incluir_legacy=True):
    """Opciones ordenadas para selectbox manteniendo un valor histórico desconocido si existe."""
    actual = normalizar_ubicacion_mexico(valor_actual)
    opciones = list(OPCIONES_UBICACION_CAPTURA)
    if incluir_legacy and actual and actual not in opciones:
        opciones.append(actual)
    return opciones

ALIASES_PERSONAS = {
    "id_institución": "id_institucion",
    "id_institucion": "id_institucion",
    "vinculación": "vinculacion",
    "vinculacion": "vinculacion",
    "año": "Año",
    "ano": "Año",
    "área_carrera": "area_carrera",
}


def inicializar_archivos():
    if not PERSONAS_FILE.exists():
        for f in ORIG_PERSONAS:
            if f.exists():
                guardar_csv_verificado(leer_csv_seguro(f), PERSONAS_FILE)
                break
        else:
            guardar_csv_verificado(pd.DataFrame(columns=PERSONAS_COLS), PERSONAS_FILE)

    if not VACANTES_FILE.exists():
        for f in ORIG_VACANTES:
            if f.exists():
                guardar_csv_verificado(leer_csv_seguro(f), VACANTES_FILE)
                break
        else:
            guardar_csv_verificado(pd.DataFrame(columns=VACANTES_COLS), VACANTES_FILE)

    if not HISTORIAL_FILE.exists():
        guardar_csv_verificado(pd.DataFrame(columns=HISTORIAL_COLS), HISTORIAL_FILE)
    if not VINCULACIONES_FILE.exists():
        guardar_csv_verificado(pd.DataFrame(columns=VINCULACIONES_COLS), VINCULACIONES_FILE)


@st.cache_data(show_spinner=False, max_entries=24)
def _leer_csv_cacheado(path_str, mtime_ns, expected_cols_tuple):
    """Lee un CSV una sola vez mientras el archivo no cambie en disco."""
    expected_cols = list(expected_cols_tuple) if expected_cols_tuple else None
    for enc in ["utf-8-sig", "utf-8", "latin1"]:
        try:
            df = pd.read_csv(path_str, encoding=enc, dtype=str)
            df.columns = df.columns.str.strip()
            if expected_cols:
                for c in expected_cols:
                    if c not in df.columns:
                        df[c] = None
                df = df[expected_cols]
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=expected_cols or [])


def leer_csv_seguro(path, expected_cols=None):
    path = Path(path)
    try:
        mtime_ns = path.stat().st_mtime_ns
    except OSError:
        mtime_ns = -1
    # .copy() evita que un módulo modifique accidentalmente el DataFrame cacheado.
    return _leer_csv_cacheado(str(path), mtime_ns, tuple(expected_cols or ())).copy()


def guardar_csv_verificado(df, path):
    """Guarda un CSV de forma atómica y verifica que pueda leerse completo.

    Primero escribe en un archivo temporal dentro de la misma carpeta y solo reemplaza
    el archivo definitivo si la escritura y la lectura de comprobación son correctas.
    Esto reduce el riesgo de archivos parciales ante cierres o fallos durante el guardado.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv.tmp", prefix=f".{path.stem}_",
            dir=path.parent, delete=False, encoding="utf-8-sig", newline=""
        ) as tmp:
            tmp_path = Path(tmp.name)
            df.to_csv(tmp, index=False)
            tmp.flush()
            os.fsync(tmp.fileno())

        comprobacion = pd.read_csv(tmp_path, encoding="utf-8-sig", dtype=str)
        if len(comprobacion) != len(df):
            raise IOError(f"Verificación fallida: se esperaban {len(df)} filas y se leyeron {len(comprobacion)}.")
        if list(comprobacion.columns) != list(df.columns):
            raise IOError("Verificación fallida: las columnas guardadas no coinciden con las esperadas.")

        os.replace(tmp_path, path)
        return path
    finally:
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def explicar_visualizacion(fuente, significado, interpretacion):
    """Muestra trazabilidad e interpretación sin saturar el dashboard."""
    with st.expander("ℹ️ Fuente, significado e interpretación"):
        st.markdown(
            f"**Fuente:** {fuente}  \n"
            f"**Qué significa:** {significado}  \n"
            f"**Cómo se interpreta:** {interpretacion}"
        )


def guardar_backup(nombre, df):
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    archivo = BACKUP_DIR / f"backup_{nombre}_{fecha}.csv"
    guardar_csv_verificado(df, archivo)
    return archivo


def leer_archivo_subido(uploaded_file):
    nombre = uploaded_file.name.lower()
    if nombre.endswith(".csv"):
        try:
            return pd.read_csv(uploaded_file, encoding="utf-8-sig", dtype=str)
        except Exception:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding="latin1", dtype=str)
    if nombre.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file, dtype=str)
    raise ValueError("Formato no soportado. Usa CSV o Excel.")


def texto_vacio(valor):
    if pd.isna(valor):
        return True
    return str(valor).strip().lower() in ["", "nan", "none", "nat"]


def normalizar_texto(valor):
    if pd.isna(valor):
        return ""
    texto = str(valor).strip().lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8")
    return " ".join(texto.split())


def _renombrar_aliases_personas(df):
    ren = {}
    existentes = set(df.columns)
    for c in df.columns:
        key = c.strip().lower()
        if key in ALIASES_PERSONAS:
            destino = ALIASES_PERSONAS[key]
            # No renombrar columnas derivadas (p. ej. "año") si el destino
            # oficial ya existe; evita columnas duplicadas al limpiar dos veces.
            if c != destino and destino not in existentes:
                ren[c] = destino
                existentes.add(destino)
    return df.rename(columns=ren)


@st.cache_data(show_spinner=False)
def limpiar_personas(df):
    """Normaliza tipos sin destruir la diferencia entre vacío e 'Indefinido'."""
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip()
    df = _renombrar_aliases_personas(df)

    if not df.empty:
        tiene_datos = df.apply(
            lambda fila: fila.map(lambda v: pd.notna(v) and str(v).strip() != "").any(), axis=1
        )
        df = df.loc[tiene_datos].copy()

    for c in PERSONAS_COLS:
        if c not in df.columns:
            df[c] = None
    df = df[PERSONAS_COLS]

    columnas_texto = [
        "id_persona", "id_persona_maestro", "nombre", "sexo", "escolaridad", "carrera",
        "Institución", "id_institucion", "municipio", "id_municipio", "telefono", "correo",
        "grupo_prioritario", "vinculacion", "Año", "area_carrera", "estatus_vinculacion"
    ]
    for col in columnas_texto:
        df[col] = df[col].astype("object").where(pd.notna(df[col]), "").astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    df["correo"] = df["correo"].str.lower()
    df["municipio"] = df["municipio"].apply(normalizar_ubicacion_mexico)
    # Todo registro histórico representa una vinculación confirmada en el esquema actual.
    df["estatus_vinculacion"] = "Vinculado"
    df["edad"] = pd.to_numeric(df["edad"], errors="coerce")
    df["fecha_registro"] = pd.to_datetime(df["fecha_registro"], errors="coerce", dayfirst=True)

    # Año explícito se conserva; cuando está vacío y existe fecha, se deriva.
    año_fecha = df["fecha_registro"].dt.year.astype("Int64").astype(str).replace("<NA>", "")
    vacio_año = df["Año"].eq("") | df["Año"].str.lower().isin(["nan", "none"])
    df.loc[vacio_año, "Año"] = año_fecha[vacio_año]

    # IDs faltantes: se generan sin colapsar registros repetidos.
    faltan_maestro = df["id_persona_maestro"].eq("") | df["id_persona_maestro"].str.lower().eq("nan")
    if faltan_maestro.any():
        inicio = siguiente_numero_maestro(df.loc[~faltan_maestro, "id_persona_maestro"])
        df.loc[faltan_maestro, "id_persona_maestro"] = [f"PER-{inicio+i:04d}" for i in range(faltan_maestro.sum())]

    faltan_registro = df["id_persona"].eq("") | df["id_persona"].str.lower().eq("nan")
    if faltan_registro.any():
        general = siguiente_numero_general_vinculacion(df.loc[~faltan_registro, "id_persona"])
        contadores = {t: siguiente_numero_tipo(df.loc[~faltan_registro, "id_persona"], PREFIJOS_VINCULACION[t]) for t in TIPOS_VINCULACION}
        nuevos = []
        for _, r in df.loc[faltan_registro].iterrows():
            tipo = r["vinculacion"] if r["vinculacion"] in PREFIJOS_VINCULACION else "Atención"
            pref = PREFIJOS_VINCULACION[tipo]
            n_tipo = contadores[tipo]
            nuevos.append(f"{pref}-{n_tipo:05d}-{general:05d}")
            contadores[tipo] += 1
            general += 1
        df.loc[faltan_registro, "id_persona"] = nuevos
    return df


def siguiente_numero_maestro(serie):
    nums = pd.Series(serie, dtype=str).str.extract(r"PER-(\d+)", expand=False)
    nums = pd.to_numeric(nums, errors="coerce")
    return int(nums.max()) + 1 if nums.notna().any() else 1


def siguiente_numero_general_vinculacion(serie):
    nums = pd.Series(serie, dtype=str).str.extract(r"-(\d+)$", expand=False)
    nums = pd.to_numeric(nums, errors="coerce")
    return int(nums.max()) + 1 if nums.notna().any() else 1


def siguiente_numero_tipo(serie, prefijo):
    nums = pd.Series(serie, dtype=str).str.extract(rf"^{prefijo}-(\d+)-", expand=False)
    nums = pd.to_numeric(nums, errors="coerce")
    return int(nums.max()) + 1 if nums.notna().any() else 1


def generar_id_registro_vinculacion(df, tipo):
    df = limpiar_personas(df)
    pref = PREFIJOS_VINCULACION.get(tipo, "A")
    return f"{pref}-{siguiente_numero_tipo(df['id_persona'], pref):05d}-{siguiente_numero_general_vinculacion(df['id_persona']):05d}"


def generar_id_persona_maestro(df):
    df = limpiar_personas(df)
    return f"PER-{siguiente_numero_maestro(df['id_persona_maestro']):04d}"


@st.cache_data(show_spinner=False)
def preparar_personas_dashboard(df):
    df = limpiar_personas(df)
    df["mes"] = df["fecha_registro"].dt.to_period("M").astype(str).replace("NaT", "")
    año_num = pd.to_numeric(df["Año"], errors="coerce")
    df["año"] = año_num.astype("Int64")
    df["grupo_edad"] = pd.cut(
        df["edad"], bins=[0, 17, 24, 29, 39, 49, 59, 100],
        labels=["Menor de 18", "18 a 24", "25 a 29", "30 a 39", "40 a 49", "50 a 59", "60 o más"]
    )
    return df


@st.cache_data(show_spinner=False)
def obtener_personas_maestras(df):
    """Una fila por persona maestra, usando el dato más informativo/reciente disponible."""
    df = preparar_personas_dashboard(df).copy()
    if df.empty:
        return df
    df["_fecha_ord"] = df["fecha_registro"].fillna(pd.Timestamp("1900-01-01"))
    df = df.sort_values(["id_persona_maestro", "_fecha_ord"])
    filas = []
    for maestro, g in df.groupby("id_persona_maestro", dropna=False):
        base = g.iloc[-1].copy()
        for col in ["nombre", "sexo", "edad", "escolaridad", "carrera", "Institución", "municipio", "telefono", "correo", "grupo_prioritario", "area_carrera"]:
            validos = g[col].dropna().astype(str)
            validos = validos[~validos.str.strip().str.lower().isin(["", "nan", "none", "indefinido"])]
            if len(validos):
                base[col] = validos.iloc[-1]
        base["total_vinculaciones"] = len(g)
        base["primera_fecha"] = g["fecha_registro"].min()
        base["ultima_fecha"] = g["fecha_registro"].max()
        base["tipos_vinculacion"] = ", ".join(sorted(set(x for x in g["vinculacion"] if str(x).strip())))
        años = pd.to_numeric(g["Año"], errors="coerce").dropna().astype(int)
        base["años_con_registro"] = ", ".join(map(str, sorted(años.unique())))
        filas.append(base)
    out = pd.DataFrame(filas).drop(columns=["_fecha_ord"], errors="ignore")
    return out.reset_index(drop=True)


def resumen_vinculaciones_por_persona(df):
    df = preparar_personas_dashboard(df)
    if df.empty:
        return pd.DataFrame(columns=["id_persona_maestro", "nombre", "total_vinculaciones"])
    nombres = obtener_personas_maestras(df).set_index("id_persona_maestro")["nombre"]
    res = df.groupby("id_persona_maestro").agg(
        total_vinculaciones=("id_persona", "count"),
        primera_fecha=("fecha_registro", "min"),
        ultima_fecha=("fecha_registro", "max"),
    ).reset_index()
    res["nombre"] = res["id_persona_maestro"].map(nombres)
    return res[["id_persona_maestro", "nombre", "total_vinculaciones", "primera_fecha", "ultima_fecha"]].sort_values(
        ["total_vinculaciones", "nombre"], ascending=[False, True]
    )


def crear_excel_plantilla(columnas):
    buffer = io.BytesIO()
    pd.DataFrame(columns=columnas).to_excel(buffer, index=False)
    buffer.seek(0)
    return buffer.getvalue()


def validar_personas(df):
    df = limpiar_personas(df)
    errores = []
    for i, fila in df.iterrows():
        if texto_vacio(fila.get("nombre")):
            errores.append({"fila": i + 1, "campo": "nombre", "error": "El nombre es obligatorio."})
        if texto_vacio(fila.get("id_persona_maestro")):
            errores.append({"fila": i + 1, "campo": "id_persona_maestro", "error": "Cada registro debe asociarse a una persona maestra."})
        edad = fila.get("edad")
        if pd.notna(edad) and (edad <= 0 or edad > 120):
            errores.append({"fila": i + 1, "campo": "edad", "error": "La edad debe estar entre 1 y 120."})
    return errores


def aplicar_duplicados_personas(df):
    """Solo un ID de registro idéntico se considera duplicado. Nombres repetidos son vinculaciones válidas."""
    df = limpiar_personas(df).copy()
    antes = len(df)
    df = df.drop_duplicates(subset=["id_persona"], keep="last")
    return df[PERSONAS_COLS], antes - len(df)


def normalizar_puesto_vacante(valor):
    """Homologa variantes claras sin inventar equivalencias entre puestos distintos."""
    if texto_vacio(valor):
        return ""
    limpio = " ".join(str(valor).strip().split())
    return ALIASES_PUESTOS_VACANTES.get(normalizar_texto(limpio), limpio)


def categoria_puesto_vacante(puesto, tipo_oportunidad="Empleo"):
    if tipo_oportunidad in ["Prácticas Profesionales", "Servicio Social"]:
        return "Formación y Vinculación"
    p = normalizar_texto(puesto)
    reglas = [
        (["ayudante", "operador", "produccion", "empacador", "hornero", "escaneador"], "Producción y Operaciones"),
        (["mantenimiento", "mecanico", "electromecanico", "electrico", "inyeccion"], "Mantenimiento y Electromecánica"),
        (["calidad", "sqa"], "Calidad"),
        (["ingeniero", "planeador"], "Ingeniería"),
        (["almacen", "almacenista", "materiales", "embarques", "comprador"], "Logística y Almacén"),
        (["contabilidad", "cuentas por cobrar", "costos", "financiero", "contador"], "Administración y Finanzas"),
        (["ventas"], "Ventas y Comercial"),
        (["capital humano", "reclutamiento"], "Recursos Humanos"),
        (["seguridad industrial", "medico industrial", "vigilante", "velador"], "Seguridad y Salud"),
        (["chofer", "tractocamion", "camion", "grua"], "Transporte"),
        (["soldador", "pailero", "carpintero", "tornero", "fresador", "montacarguista", "pintor"], "Oficios y Técnicos"),
        (["textil", "costura", "serigrafista", "tejedor", "cardero", "hilador", "atador"], "Textil"),
    ]
    for palabras, categoria in reglas:
        if any(x in p for x in palabras):
            return categoria
    return "Otros"


def asegurar_ids_vacantes(df):
    """Asigna IDs únicamente a filas nuevas y conserva los IDs históricos existentes."""
    df = df.copy()
    for c in ["ID Vacante", "ID Registro Origen"]:
        if c not in df.columns:
            df[c] = ""
        df[c] = df[c].fillna("").astype(str).str.strip()

    nums = pd.to_numeric(df["ID Vacante"].str.extract(r"VAC-(\d+)", expand=False), errors="coerce")
    siguiente = int(nums.max()) + 1 if nums.notna().any() else 1
    for idx in df.index[df["ID Vacante"].eq("")]:
        df.at[idx, "ID Vacante"] = f"VAC-{siguiente:04d}"
        siguiente += 1

    nums_o = pd.to_numeric(df["ID Registro Origen"].str.extract(r"ORI-(\d+)", expand=False), errors="coerce")
    siguiente_o = int(nums_o.max()) + 1 if nums_o.notna().any() else 1
    for idx in df.index[df["ID Registro Origen"].eq("")]:
        df.at[idx, "ID Registro Origen"] = f"ORI-{siguiente_o:04d}"
        siguiente_o += 1
    return df


@st.cache_data(show_spinner=False)
def limpiar_vacantes(df):
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip()

    # Compatibilidad con archivos antiguos: conservar el texto original antes de homologar.
    if "Puesto Original" not in df.columns:
        df["Puesto Original"] = df["Tipo de Vacante"] if "Tipo de Vacante" in df.columns else ""
    for c in VACANTES_COLS:
        if c not in df.columns:
            df[c] = ""
    df = df[VACANTES_COLS]
    df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")

    for col in [c for c in VACANTES_COLS if c != "Fecha"]:
        df[col] = df[col].fillna("").astype(str).str.strip().str.replace(r"\s+", " ", regex=True)

    df["Puesto Original"] = df["Puesto Original"].where(df["Puesto Original"].ne(""), df["Tipo de Vacante"])
    df["Tipo de Vacante"] = df["Tipo de Vacante"].apply(normalizar_puesto_vacante)

    # Deducir tipo de oportunidad en archivos antiguos y mantenerlo consistente en nuevas capturas.
    vacio_tipo = df["Tipo de Oportunidad"].eq("")
    puesto_key = df["Tipo de Vacante"].map(normalizar_texto)
    df.loc[vacio_tipo & puesto_key.str.contains("practicas profesionales", na=False), "Tipo de Oportunidad"] = "Prácticas Profesionales"
    df.loc[vacio_tipo & puesto_key.str.contains("servicio social", na=False), "Tipo de Oportunidad"] = "Servicio Social"
    df.loc[df["Tipo de Oportunidad"].eq(""), "Tipo de Oportunidad"] = "Empleo"

    # Categoría se deriva para que capturas posteriores sigan usando el mismo catálogo analítico.
    vacia_cat = df["Categoría de Puesto"].eq("")
    df.loc[vacia_cat, "Categoría de Puesto"] = df.loc[vacia_cat].apply(
        lambda r: categoria_puesto_vacante(r["Tipo de Vacante"], r["Tipo de Oportunidad"]), axis=1
    )

    estado = df["Estado"].str.lower()
    df["Estado"] = estado.map({"activa": "Activa", "inactiva": "Inactiva", "finalizada": "Inactiva"}).fillna("Activa")
    return df


@st.cache_data(show_spinner=False)
def preparar_vacantes_dashboard(df):
    df = limpiar_vacantes(df)
    df["Mes"] = df["Fecha"].dt.to_period("M").astype(str)
    df["Año"] = df["Fecha"].dt.year
    df["MesNombre"] = df["Fecha"].dt.strftime("%b %Y")
    return df


def validar_vacantes(df):
    df = limpiar_vacantes(df)
    errores = []
    for i, fila in df.iterrows():
        if pd.isna(fila.get("Fecha")):
            errores.append({"fila": i+1, "campo": "Fecha", "error": "La fecha es obligatoria y debe ser válida."})
        if texto_vacio(fila.get("Empresa")):
            errores.append({"fila": i+1, "campo": "Empresa", "error": "La empresa es obligatoria."})
        if texto_vacio(fila.get("Tipo de Vacante")):
            errores.append({"fila": i+1, "campo": "Tipo de Vacante", "error": "El puesto es obligatorio."})
        if fila.get("Tipo de Oportunidad") not in TIPOS_OPORTUNIDAD:
            errores.append({"fila": i+1, "campo": "Tipo de Oportunidad", "error": "Usa Empleo, Prácticas Profesionales o Servicio Social."})
        if fila.get("Estado") not in ESTADOS_VACANTE:
            errores.append({"fila": i+1, "campo": "Estado", "error": "El estado debe ser Activa o Inactiva."})
    return errores


def aplicar_duplicados_vacantes(df):
    """Una misma publicación puede contener muchos puestos; el link por sí solo nunca es duplicado."""
    df = limpiar_vacantes(df).copy()
    antes = len(df)
    df["_link"] = df["Link de la Publicación"].map(normalizar_texto)
    df["_empresa"] = df["Empresa"].map(normalizar_texto)
    df["_tipo"] = df["Tipo de Vacante"].map(normalizar_texto)
    df["_area"] = df["Área de Oportunidad"].map(normalizar_texto)
    df["_oportunidad"] = df["Tipo de Oportunidad"].map(normalizar_texto)
    df["_desc"] = df["Descripción"].map(normalizar_texto)
    df["_fecha"] = df["Fecha"].dt.strftime("%Y-%m-%d")
    # Duplicado = misma fecha + empresa + puesto + oportunidad + área; el link refuerza, no colapsa puestos distintos.
    df["_dup"] = df.apply(
        lambda r: "|".join([str(r["_fecha"]), r["_empresa"], r["_tipo"], r["_oportunidad"], r["_area"], r["_link"], r["_desc"]]), axis=1
    )
    df = df.drop_duplicates("_dup", keep="last").drop(columns=["_link","_empresa","_tipo","_area","_oportunidad","_desc","_fecha","_dup"])
    df = asegurar_ids_vacantes(df)
    return df[VACANTES_COLS], antes-len(df)

def registrar_historial(usuario, base, origen, archivo_origen, recibidos, guardados, duplicados, total):
    nuevo = pd.DataFrame([{
        "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "usuario": usuario or "No especificado",
        "base": base, "origen": origen, "archivo_origen": archivo_origen or "Captura manual",
        "registros_recibidos": recibidos, "registros_guardados": guardados,
        "duplicados_actualizados": duplicados, "total_final": total,
    }])
    # El historial se centraliza cuando Supabase está configurado y, además,
    # se conserva una copia local como respaldo operativo.
    if cloud_enabled():
        try:
            cloud_insert_df("historial", nuevo)
        except Exception as e:
            st.warning(f"No se pudo registrar el movimiento en el historial de nube: {e}")
    historial = leer_csv_seguro(HISTORIAL_FILE, HISTORIAL_COLS)
    guardar_csv_verificado(pd.concat([historial, nuevo], ignore_index=True), HISTORIAL_FILE)


def _guardar_espejo_local(tipo, df):
    archivo = {"personas": PERSONAS_FILE, "vacantes": VACANTES_FILE, "vinculaciones": VINCULACIONES_FILE}.get(tipo)
    if archivo is not None:
        guardar_csv_verificado(df, archivo)


def _session_cache_get(tipo, ttl=8):
    cache = st.session_state.get("_cloud_df_cache", {})
    item = cache.get(tipo)
    if not item:
        return None
    ts, df = item
    if time.monotonic() - ts > ttl:
        return None
    return df.copy()


def _session_cache_set(tipo, df):
    cache = st.session_state.setdefault("_cloud_df_cache", {})
    cache[tipo] = (time.monotonic(), df.copy())


def _session_cache_clear(tipo=None):
    if tipo is None:
        st.session_state.pop("_cloud_df_cache", None)
        return
    cache = st.session_state.get("_cloud_df_cache", {})
    cache.pop(tipo, None)


def _cargar_cloud_o_local(tipo):
    if cloud_enabled():
        cached = _session_cache_get(tipo)
        if cached is not None:
            return cached
        try:
            df = cloud_fetch_all(tipo)
            _guardar_espejo_local(tipo, df)
            _session_cache_set(tipo, df)
            return df
        except Exception as e:
            st.warning(f"⚠️ No se pudo consultar Supabase ({tipo}). Se muestra el último espejo local. No se realizarán escrituras locales mientras la nube esté configurada. Detalle: {e}")
    if tipo == "personas": return leer_csv_seguro(PERSONAS_FILE)
    if tipo == "vacantes": return leer_csv_seguro(VACANTES_FILE, VACANTES_COLS)
    if tipo == "vinculaciones": return leer_csv_seguro(VINCULACIONES_FILE)
    return pd.DataFrame()


def insertar_y_guardar(df_actual, df_nuevo, tipo, usuario="No especificado", origen="manual", archivo_origen="Captura manual", quitar_duplicados=True):
    from utils.auth import has_permission
    if not has_permission(tipo, "create"):
        return {"ok": False, "errores": [{"campo":"Permisos", "error":"No tienes permiso para crear registros en este módulo."}]}
    if tipo == "personas":
        df_nuevo = limpiar_personas(df_nuevo); errores = validar_personas(df_nuevo); dedup = aplicar_duplicados_personas
        id_col = "id_persona"
    else:
        df_nuevo = limpiar_vacantes(df_nuevo); errores = validar_vacantes(df_nuevo); dedup = aplicar_duplicados_vacantes
        id_col = "ID Vacante"
    if errores: return {"ok": False, "errores": errores}

    # En nube siempre se vuelve a leer el estado más reciente antes de fusionar,
    # evitando que una PC sobrescriba altas hechas segundos antes por otra.
    actual = cargar_personas_base() if tipo == "personas" else cargar_vacantes_base()
    actual = limpiar_personas(actual) if tipo == "personas" else limpiar_vacantes(actual)
    guardar_backup(tipo, actual)

    # Resolver colisiones de IDs generados desde otra computadora.
    existentes=set(actual[id_col].fillna("").astype(str))
    if tipo == "personas":
        for i in df_nuevo.index:
            rid=str(df_nuevo.at[i,"id_persona"]).strip()
            if rid and rid in existentes:
                tipo_v=df_nuevo.at[i,"vinculacion"] if df_nuevo.at[i,"vinculacion"] in TIPOS_VINCULACION else "Atención"
                df_nuevo.at[i,"id_persona"] = generar_id_registro_vinculacion(pd.concat([actual,df_nuevo.loc[:i-1]],ignore_index=True), tipo_v)
            existentes.add(str(df_nuevo.at[i,"id_persona"]))
    else:
        colision=df_nuevo[id_col].astype(str).isin(existentes)
        if colision.any():
            df_nuevo.loc[colision,id_col]=""
            combinado_ids = asegurar_ids_vacantes(pd.concat([actual, df_nuevo], ignore_index=True))
            df_nuevo = combinado_ids.tail(len(df_nuevo)).reset_index(drop=True)

    combinado = pd.concat([actual, df_nuevo], ignore_index=True)
    duplicados = 0
    if quitar_duplicados:
        combinado, duplicados = dedup(combinado)
    if tipo == "vacantes": combinado = asegurar_ids_vacantes(combinado)

    if cloud_enabled():
        try:
            # Upsert del resultado final: no elimina filas agregadas concurrentemente.
            cloud_upsert_df(tipo, combinado)
            _session_cache_clear(tipo)
            final = cloud_fetch_all(tipo)
            _session_cache_set(tipo, final)
            _guardar_espejo_local(tipo, final)
        except Exception as e:
            return {"ok": False, "errores": [{"campo":"Supabase", "error":f"No se guardó nada localmente porque falló la base central: {e}"}]}
    else:
        final = combinado
        _guardar_espejo_local(tipo, final)

    guardados = max(len(df_nuevo)-duplicados, 0)
    registrar_historial(usuario, tipo, origen, archivo_origen, len(df_nuevo), guardados, duplicados, len(final))
    return {"ok": True, "recibidos": len(df_nuevo), "guardados": guardados, "duplicados": duplicados, "total": len(final)}


def guardar_registro_editado(tipo, fila_df, usuario="No especificado", accion="edición"):
    """Actualiza únicamente el registro seleccionado; seguro frente a otras PCs."""
    from utils.auth import has_permission
    if not has_permission(tipo, "edit"):
        return {"ok": False, "errores": [{"campo":"Permisos", "error":"No tienes permiso para editar registros en este módulo."}]}
    if tipo == "personas":
        fila_df=limpiar_personas(fila_df); errores=validar_personas(fila_df); id_col="id_persona"
    elif tipo == "vacantes":
        fila_df=limpiar_vacantes(fila_df); errores=validar_vacantes(fila_df); id_col="ID Vacante"
    else:
        fila_df=limpiar_vinculaciones(fila_df); errores=[]; id_col="id_vinculacion"
    if errores: return {"ok":False,"errores":errores}
    actual = _cargar_cloud_o_local(tipo)
    guardar_backup(tipo, actual)
    if cloud_enabled():
        try:
            cloud_upsert_df(tipo, fila_df)
            final=cloud_fetch_all(tipo); _guardar_espejo_local(tipo, final)
        except Exception as e:
            return {"ok":False,"errores":[{"campo":"Supabase","error":str(e)}]}
    else:
        limpio = limpiar_personas(actual) if tipo=="personas" else limpiar_vacantes(actual) if tipo=="vacantes" else limpiar_vinculaciones(actual)
        rid=str(fila_df.iloc[0][id_col]); mask=limpio[id_col].astype(str).eq(rid)
        if mask.any():
            for c in fila_df.columns: limpio.loc[mask,c]=fila_df.iloc[0][c]
        else: limpio=pd.concat([limpio,fila_df],ignore_index=True)
        final=limpio; _guardar_espejo_local(tipo, final)
    registrar_historial(usuario,tipo,accion,"Edición desde app",1,1,0,len(final))
    return {"ok":True,"total":len(final)}


def eliminar_registro(tipo, id_valor, usuario="SEDECO", accion="eliminación"):
    from utils.auth import has_permission
    if not has_permission(tipo, "delete"):
        return {"ok": False, "errores": [{"campo":"Permisos", "error":"No tienes permiso para eliminar registros en este módulo."}]}
    cfg={"personas":("id_persona",limpiar_personas),"vacantes":("ID Vacante",limpiar_vacantes),"vinculaciones":("id_vinculacion",limpiar_vinculaciones)}
    id_col, cleaner=cfg[tipo]
    actual=cleaner(_cargar_cloud_o_local(tipo)); guardar_backup(tipo,actual)
    if cloud_enabled():
        try:
            cloud_delete_ids(tipo,[id_valor]); final=cloud_fetch_all(tipo); _guardar_espejo_local(tipo,final)
        except Exception as e:
            return {"ok":False,"errores":[{"campo":"Supabase","error":str(e)}]}
    else:
        final=actual[~actual[id_col].astype(str).eq(str(id_valor))].reset_index(drop=True); _guardar_espejo_local(tipo,final)
    registrar_historial(usuario,tipo,accion,"Eliminación desde app",1,1,0,len(final))
    return {"ok":True,"total":len(final)}


def guardar_base_editada(tipo, df, usuario="No especificado", accion="edición", permitir_cambio_filas=False):
    from utils.auth import has_permission
    if not has_permission(tipo, "edit"):
        return {"ok": False, "errores": [{"campo":"Permisos", "error":"No tienes permiso para editar registros en este módulo."}]}
    # Compatibilidad con módulos antiguos. Las pantallas actuales usan guardar_registro_editado/eliminar_registro.
    if tipo == "personas":
        df=limpiar_personas(df); errores=validar_personas(df)
    else:
        df=limpiar_vacantes(df); errores=validar_vacantes(df)
    if errores: return {"ok":False,"errores":errores}
    if cloud_enabled():
        try:
            cloud_upsert_df(tipo,df); final=cloud_fetch_all(tipo); _guardar_espejo_local(tipo,final)
        except Exception as e:
            return {"ok":False,"errores":[{"campo":"Supabase","error":str(e)}]}
    else:
        final=df; _guardar_espejo_local(tipo,final)
    registrar_historial(usuario,tipo,accion,"Edición desde app",len(df),len(df),0,len(final))
    return {"ok":True,"total":len(final)}


def cargar_personas_base(): return _cargar_cloud_o_local("personas")
def cargar_vacantes_base(): return _cargar_cloud_o_local("vacantes")
def cargar_vinculaciones_base(): return _cargar_cloud_o_local("vinculaciones")


def limpiar_vinculaciones(df):
    df = df.copy(); df.columns = df.columns.astype(str).str.strip()
    # Migración desde el esquema anterior: id_persona se entendía como registro histórico.
    if "id_persona_maestro" not in df.columns:
        df["id_persona_maestro"] = ""
    if "id_registro_origen" not in df.columns:
        df["id_registro_origen"] = df["id_persona"] if "id_persona" in df.columns else ""
    if "id_persona" in df.columns:
        personas = limpiar_personas(cargar_personas_base())
        mapa = personas.drop_duplicates("id_persona").set_index("id_persona")["id_persona_maestro"].to_dict()
        falta = df["id_persona_maestro"].fillna("").astype(str).str.strip().eq("")
        df.loc[falta, "id_persona_maestro"] = df.loc[falta, "id_persona"].astype(str).map(mapa).fillna("")

    if "estatus" not in df.columns:
        df["estatus"] = "Vinculado"
    mapa_estatus = {
        "sin vincular":"No vinculado", "pendiente":"No vinculado", "pendiente de aceptación":"No vinculado",
        "entrevista programada":"No vinculado", "aceptado":"Vinculado", "contratado":"Colocado", "colocado":"Colocado",
        "rechazado":"No vinculado", "baja":"No vinculado", "vinculado":"Vinculado", "no vinculado":"No vinculado"
    }
    df["estatus"] = df["estatus"].fillna("").astype(str).str.strip().str.lower().map(mapa_estatus).fillna("Vinculado")
    if "fecha_vinculacion" not in df.columns:
        df["fecha_vinculacion"] = None
    if "fecha_colocacion" not in df.columns:
        df["fecha_colocacion"] = None
    if "fecha_respuesta" in df.columns:
        m = df["estatus"].eq("Vinculado") & pd.isna(df["fecha_vinculacion"])
        df.loc[m, "fecha_vinculacion"] = df.loc[m, "fecha_respuesta"]
    # Compatibilidad: fecha_envio de versiones anteriores se ignora deliberadamente.
    for c in VINCULACIONES_COLS:
        if c not in df.columns:
            df[c] = None
    df = df[VINCULACIONES_COLS]
    for col in ["id_vinculacion","id_persona_maestro","id_registro_origen","nombre_persona","empresa","sector_empresa","tipo_vacante","area_oportunidad","estatus","observaciones","responsable"]:
        df[col] = df[col].fillna("").astype(str).str.strip()
    df["fecha_vinculacion"] = pd.to_datetime(df["fecha_vinculacion"], errors="coerce", dayfirst=True)
    df["fecha_colocacion"] = pd.to_datetime(df["fecha_colocacion"], errors="coerce", dayfirst=True)
    df["fecha_actualizacion"] = df["fecha_actualizacion"].fillna("").astype(str)
    df.loc[df["empresa"].eq(""), "empresa"] = "Sin asignar"
    df.loc[df["tipo_vacante"].eq(""), "tipo_vacante"] = "Sin asignar"
    df.loc[df["responsable"].eq(""), "responsable"] = "SEDECO"
    faltan = df["id_vinculacion"].eq("") | df["id_vinculacion"].str.lower().eq("nan")
    if faltan.any():
        base = datetime.now().strftime("%Y%m%d%H%M%S")
        df.loc[faltan, "id_vinculacion"] = [f"VIN-{base}-{i+1}" for i in range(faltan.sum())]
    return df


def aplicar_duplicados_vinculaciones(df):
    df = limpiar_vinculaciones(df).copy(); antes = len(df)
    # Solo el mismo ID de seguimiento se actualiza. Una persona puede tener N seguimientos.
    df = df.drop_duplicates(subset=["id_vinculacion"], keep="last")
    return df[VINCULACIONES_COLS], antes-len(df)


def guardar_vinculaciones_base(df, usuario="SEDECO", accion="edición", quitar_duplicados=True):
    from utils.auth import has_permission
    action = "create" if any(x in str(accion).lower() for x in ["nuevo", "alta", "captura"]) else "edit"
    if not has_permission("vinculaciones", action):
        return {"ok":False,"errores":[{"campo":"Permisos","error":f"No tienes permiso para {action} en vinculaciones."}],"total":0,"duplicados":0}
    df=limpiar_vinculaciones(df); actual=limpiar_vinculaciones(cargar_vinculaciones_base()); guardar_backup("vinculaciones",actual)
    duplicados=0
    if quitar_duplicados: df,duplicados=aplicar_duplicados_vinculaciones(df)
    if cloud_enabled():
        try:
            # Upsert conserva seguimientos creados simultáneamente desde otras PCs.
            cloud_upsert_df("vinculaciones",df)
            final=cloud_fetch_all("vinculaciones"); _guardar_espejo_local("vinculaciones",final)
        except Exception as e:
            return {"ok":False,"errores":[{"campo":"Supabase","error":str(e)}],"total":len(actual),"duplicados":duplicados}
    else:
        final=df; _guardar_espejo_local("vinculaciones",final)
    registrar_historial(usuario,"vinculaciones",accion,"Seguimiento desde app",len(df),len(df),duplicados,len(final))
    return {"ok":True,"total":len(final),"duplicados":duplicados}


def estado_persona_vinculacion(id_persona_maestro, vinculaciones=None):
    if vinculaciones is None: vinculaciones = cargar_vinculaciones_base()
    v = limpiar_vinculaciones(vinculaciones)
    persona = v[v["id_persona_maestro"].astype(str) == str(id_persona_maestro)]
    if persona.empty: return "Vinculado", 0, ""
    persona = persona.sort_values(["fecha_actualizacion", "fecha_vinculacion"])
    fila = persona.iloc[-1]
    empresas = persona.loc[persona["empresa"].ne("Sin asignar"), "empresa"].nunique()
    empresa = fila["empresa"] if fila["empresa"] != "Sin asignar" else ""
    return fila["estatus"], int(empresas), empresa if fila["estatus"] in {"Vinculado", "Colocado"} else ""


def generar_bases_por_estatus():
    personas = obtener_personas_maestras(cargar_personas_base())
    vinculaciones = limpiar_vinculaciones(cargar_vinculaciones_base())
    resumen = []
    for _, p in personas.iterrows():
        estado, total_empresas, empresa_final = estado_persona_vinculacion(p.get("id_persona_maestro"), vinculaciones)
        r = p.to_dict(); r["estatus_general"] = estado; r["empresas_vinculadas"] = total_empresas; r["empresa_final"] = empresa_final; resumen.append(r)
    df = pd.DataFrame(resumen)
    vinculados = df[df["estatus_general"].eq("Vinculado")] if not df.empty else df
    pendientes = df[df["estatus_general"].eq("Pendiente")] if not df.empty else df
    no_vinculados = df[df["estatus_general"].eq("No vinculado")] if not df.empty else df
    guardar_csv_verificado(vinculados, VINCULADOS_FILE)
    guardar_csv_verificado(pendientes, PENDIENTES_FILE)
    guardar_csv_verificado(no_vinculados, NO_VINCULADOS_FILE)
    return vinculados, pendientes, no_vinculados
