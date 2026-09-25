"""Acceso centralizado a Supabase para Vincúlate SEDECO.

La app conserva DataFrames con los nombres históricos de columnas, mientras que
PostgreSQL usa nombres snake_case. Si SUPABASE_URL/SUPABASE_KEY no están
configurados, la aplicación sigue funcionando en modo CSV local.
"""
from __future__ import annotations

import os
from datetime import date, datetime
import time
from typing import Dict, Iterable, List

import pandas as pd
import streamlit as st

try:
    from supabase import create_client
except Exception:  # permite abrir la app local aun si no se instaló la dependencia
    create_client = None

TABLES = {
    "personas": {
        "table": "personas",
        "pk": "id_persona",
        "local_pk": "id_persona",
        "map": {
            "id_persona":"id_persona", "id_persona_maestro":"id_persona_maestro",
            "nombre":"nombre", "sexo":"sexo", "edad":"edad", "escolaridad":"escolaridad",
            "carrera":"carrera", "Institución":"institucion", "id_institucion":"id_institucion",
            "municipio":"municipio", "id_municipio":"id_municipio", "telefono":"telefono",
            "correo":"correo", "grupo_prioritario":"grupo_prioritario", "vinculacion":"vinculacion",
            "fecha_registro":"fecha_registro", "Año":"anio", "area_carrera":"area_carrera",
            "estatus_vinculacion":"estatus_vinculacion",
        },
        "integers": {"edad", "anio"},
        "dates": {"fecha_registro"},
    },
    "vacantes": {
        "table": "vacantes", "pk": "id_vacante", "local_pk":"ID Vacante",
        "map": {
            "ID Vacante":"id_vacante", "ID Registro Origen":"id_registro_origen",
            "Actividad":"actividad", "Fecha":"fecha", "Empresa":"empresa",
            "Sector Empresa":"sector_empresa", "Puesto Original":"puesto_original",
            "Tipo de Vacante":"tipo_vacante", "Categoría de Puesto":"categoria_puesto",
            "Tipo de Oportunidad":"tipo_oportunidad", "Área de Oportunidad":"area_oportunidad",
            "Descripción":"descripcion", "Requisitos":"requisitos", "Beneficios":"beneficios",
            "Link de la Publicación":"link_publicacion", "Estado":"estado",
        },
        "integers": set(),
        "dates": {"fecha"},
    },
    "vinculaciones": {
        "table":"vinculaciones", "pk":"id_vinculacion", "local_pk":"id_vinculacion",
        "map": {
            "id_vinculacion":"id_vinculacion", "id_persona_maestro":"id_persona_maestro",
            "id_registro_origen":"id_registro_origen", "nombre_persona":"nombre_persona",
            "empresa":"empresa", "sector_empresa":"sector_empresa", "tipo_vacante":"tipo_vacante",
            "area_oportunidad":"area_oportunidad", "estatus":"estatus",
            "fecha_vinculacion":"fecha_vinculacion", "fecha_colocacion":"fecha_colocacion", "observaciones":"observaciones",
            "responsable":"responsable", "fecha_actualizacion":"fecha_actualizacion",
        },
        "integers": set(),
        "dates": {"fecha_vinculacion", "fecha_colocacion"},
    },
    "historial": {
        "table":"historial_cargas", "pk":"id", "local_pk":None,
        "map": {
            "fecha_hora":"fecha_hora", "usuario":"usuario", "base":"base", "origen":"origen",
            "archivo_origen":"archivo_origen", "registros_recibidos":"registros_recibidos",
            "registros_guardados":"registros_guardados", "duplicados_actualizados":"duplicados_actualizados",
            "total_final":"total_final",
        },
        "integers": {"registros_recibidos", "registros_guardados", "duplicados_actualizados", "total_final"},
        "dates": set(),
    },
}


def _settings():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY", "").strip()
    try:
        sec = st.secrets.get("supabase", {})
        url = str(sec.get("url", url)).strip()
        key = str(sec.get("key", key)).strip()
    except Exception:
        pass
    return url, key


def cloud_enabled() -> bool:
    url, key = _settings()
    return bool(url and key)


@st.cache_resource(show_spinner=False)
def _public_client():
    url, key = _settings()
    if not url or not key:
        raise RuntimeError("Supabase no está configurado. Agrega URL y KEY en .streamlit/secrets.toml.")
    if create_client is None:
        raise RuntimeError("Falta instalar la dependencia 'supabase'. Ejecuta pip install -r requirements.txt.")
    return create_client(url, key)


def get_client():
    # Tras iniciar sesión, todas las lecturas/escrituras usan el JWT del usuario.
    # Esto hace que las políticas RLS de Supabase sean realmente aplicables.
    auth_client = st.session_state.get("_supabase_client")
    if auth_client is not None:
        return auth_client
    return _public_client()


def ping_cloud(force: bool = False, max_age: int = 12):
    if not cloud_enabled():
        return False, "No configurado"
    now = time.monotonic()
    cached = st.session_state.get("_cloud_ping")
    if not force and cached:
        ts, ok, msg = cached
        if now - ts < max_age:
            return ok, msg
    try:
        get_client().table("personas").select("id_persona", count="exact").limit(1).execute()
        result = (True, "Conectado")
    except Exception as e:
        result = (False, str(e))
    st.session_state["_cloud_ping"] = (now, result[0], result[1])
    return result


def _scalar(v):
    if v is None:
        return None
    if not isinstance(v, (list, dict)):
        try:
            if pd.isna(v):
                return None
        except Exception:
            pass
    if isinstance(v, pd.Timestamp):
        return None if pd.isna(v) else v.isoformat()
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    # numpy scalars
    if hasattr(v, "item"):
        try:
            v = v.item()
        except Exception:
            pass
    if isinstance(v, str):
        s = v.strip()
        return None if s.lower() in {"", "nan", "none", "nat", "<na>"} else s
    return v


def _integer(v, field: str):
    """Convierte valores de pandas/Streamlit a INTEGER válido para PostgreSQL.

    Acepta 22, 22.0, numpy.int64, "22" y "22.0". Los vacíos se mandan
    como NULL. Rechaza decimales reales (ej. 22.5) para no truncar datos.
    """
    v = _scalar(v)
    if v is None:
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"El campo {field} debe ser entero; se recibió {v!r}.")
    if not n.is_integer():
        raise ValueError(f"El campo {field} debe ser entero; se recibió {v!r}.")
    return int(n)


def _date_value(v, field: str):
    """Devuelve fechas ISO YYYY-MM-DD aptas para columnas DATE."""
    v = _scalar(v)
    if v is None:
        return None
    if isinstance(v, str):
        # pandas entiende tanto ISO como fechas DD/MM/YYYY usadas históricamente.
        parsed = pd.to_datetime(v, errors="coerce", dayfirst=True)
        if pd.isna(parsed):
            raise ValueError(f"El campo {field} contiene una fecha inválida: {v!r}.")
        return parsed.date().isoformat()
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    parsed = pd.to_datetime(v, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"El campo {field} contiene una fecha inválida: {v!r}.")
    return parsed.date().isoformat()


def local_to_cloud(kind: str, df: pd.DataFrame) -> List[dict]:
    cfg = TABLES[kind]
    mp = cfg["map"]
    integer_fields = cfg.get("integers", set())
    date_fields = cfg.get("dates", set())
    rows = []
    for _, r in df.iterrows():
        row = {}
        for local, remote in mp.items():
            if local not in df.columns:
                continue
            value = r[local]
            if remote in integer_fields:
                row[remote] = _integer(value, local)
            elif remote in date_fields:
                row[remote] = _date_value(value, local)
            else:
                row[remote] = _scalar(value)
        rows.append(row)
    return rows


def cloud_to_local(kind: str, rows: List[dict]) -> pd.DataFrame:
    cfg=TABLES[kind]; inv={v:k for k,v in cfg["map"].items()}
    if not rows:
        return pd.DataFrame(columns=list(cfg["map"].keys()))
    df=pd.DataFrame(rows).rename(columns=inv)
    cols=list(cfg["map"].keys())
    for c in cols:
        if c not in df.columns: df[c]=""
    return df[cols]


def fetch_all(kind: str, page_size: int=1000) -> pd.DataFrame:
    cfg=TABLES[kind]; client=get_client(); rows=[]; start=0
    while True:
        resp=client.table(cfg["table"]).select("*").range(start, start+page_size-1).execute()
        batch=resp.data or []
        rows.extend(batch)
        if len(batch)<page_size: break
        start += page_size
    return cloud_to_local(kind, rows)


def upsert_df(kind: str, df: pd.DataFrame, chunk_size: int=300):
    cfg=TABLES[kind]; rows=local_to_cloud(kind, df)
    if not rows: return 0
    client=get_client(); total=0
    for i in range(0,len(rows),chunk_size):
        chunk=rows[i:i+chunk_size]
        kwargs={}
        if cfg["pk"]: kwargs["on_conflict"]=cfg["pk"]
        resp=client.table(cfg["table"]).upsert(chunk, **kwargs).execute()
        total += len(resp.data or chunk)
    return total


def insert_df(kind: str, df: pd.DataFrame, chunk_size: int=300):
    cfg=TABLES[kind]; rows=local_to_cloud(kind, df)
    if not rows: return 0
    client=get_client(); total=0
    for i in range(0,len(rows),chunk_size):
        chunk=rows[i:i+chunk_size]
        resp=client.table(cfg["table"]).insert(chunk).execute()
        total += len(resp.data or chunk)
    return total


def delete_ids(kind: str, ids: Iterable[str]):
    cfg=TABLES[kind]; ids=[str(x) for x in ids if str(x).strip()]
    if not ids: return 0
    client=get_client(); total=0
    for i in range(0,len(ids),100):
        chunk=ids[i:i+100]
        resp=client.table(cfg["table"]).delete().in_(cfg["pk"], chunk).execute()
        total += len(resp.data or chunk)
    return total


def count_rows(kind: str) -> int:
    cfg=TABLES[kind]
    resp=get_client().table(cfg["table"]).select(cfg["pk"] or "*", count="exact").limit(1).execute()
    return int(resp.count or 0)
