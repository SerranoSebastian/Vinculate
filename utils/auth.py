from __future__ import annotations

import os
import platform
import re
import time
import socket
import uuid
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

try:
    from supabase import create_client
except Exception:
    create_client = None

BASE_DIR = Path(__file__).resolve().parents[1]
DEVICE_FILE = BASE_DIR / ".vinculate_device_id"

MODULES = {
    "inicio": "Inicio",
    "personas": "Personas",
    "vacantes": "Vacantes",
    "vinculaciones": "Vinculaciones",
    "explorador": "Explorador general",
    "ridet": "Análisis territorial RIDET",
    "administracion": "Administración",
    "usuarios": "Usuarios y permisos",
    "dispositivos": "Computadoras autorizadas",
    "prioridades": "Prioridades y recordatorios",
    "auditoria": "Auditoría",
    "respaldos": "Respaldos",
}
ACTIONS = ("view", "create", "edit", "delete", "export")


def _settings():
    from utils.cloud_db import _settings as cloud_settings
    return cloud_settings()


def _new_client():
    url, key = _settings()
    if not url or not key:
        raise RuntimeError("Supabase no está configurado.")
    if create_client is None:
        raise RuntimeError("Falta instalar la dependencia supabase.")
    return create_client(url, key)


def authenticated_client():
    return st.session_state.get("_supabase_client")


def current_user():
    return st.session_state.get("auth_user") or {}


def current_profile():
    return st.session_state.get("auth_profile") or {}


def is_authenticated() -> bool:
    return bool(current_user().get("id") and authenticated_client())


def is_admin() -> bool:
    p = current_profile()
    return p.get("role") == "admin" and p.get("status") == "active"


def has_permission(module_key: str, action: str = "view") -> bool:
    if not is_authenticated():
        return False
    if is_admin():
        return True
    if current_profile().get("status") != "active":
        return False
    perms = st.session_state.get("auth_permissions", {})
    row = perms.get(module_key, {})
    return bool(row.get(f"can_{action}", False))


def require_permission(module_key: str, action: str = "view"):
    if not has_permission(module_key, action):
        st.error("Tu perfil no tiene permiso para realizar esta acción.")
        st.stop()


def _device_id() -> str:
    try:
        if DEVICE_FILE.exists():
            value = DEVICE_FILE.read_text(encoding="utf-8").strip()
            if value:
                return value
        value = str(uuid.uuid4())
        DEVICE_FILE.write_text(value, encoding="utf-8")
        return value
    except Exception:
        # Fallback estable razonable dentro de la instalación actual.
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{socket.gethostname()}-{BASE_DIR}"))


def _load_profile_and_permissions(client, uid: str):
    prof_resp = client.table("app_profiles").select("*").eq("user_id", uid).limit(1).execute()
    rows = prof_resp.data or []
    if not rows:
        raise PermissionError("Tu cuenta existe en Authentication, pero todavía no tiene un perfil de Vincúlate.")
    profile = rows[0]
    if profile.get("status") != "active":
        raise PermissionError(f"Tu perfil está en estado '{profile.get('status', 'sin definir')}'. Solicita activación a un administrador.")
    st.session_state["auth_profile"] = profile

    perm_resp = client.table("app_permissions").select("*").eq("user_id", uid).execute()
    st.session_state["auth_permissions"] = {
        r.get("module_key"): r for r in (perm_resp.data or []) if r.get("module_key")
    }


def refresh_authorization(force: bool = False, max_age: int = 8):
    client = authenticated_client()
    uid = current_user().get("id")
    if not client or not uid:
        return
    now = time.monotonic()
    last = float(st.session_state.get("_auth_checked_at", 0) or 0)
    if not force and st.session_state.get("auth_profile") and (now - last) < max_age:
        return
    _load_profile_and_permissions(client, uid)
    st.session_state["_auth_checked_at"] = now


def _register_or_check_device(client, uid: str) -> dict:
    did = _device_id()
    st.session_state["device_id"] = did
    resp = client.table("app_devices").select("*").eq("user_id", uid).eq("device_id", did).limit(1).execute()
    rows = resp.data or []
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "user_id": uid,
        "device_id": did,
        "hostname": socket.gethostname(),
        "os_name": platform.system(),
        "os_version": platform.version(),
        "app_version": "2026.09-perfiles",
    }
    if not rows:
        payload["authorized"] = bool(is_admin())
        created = client.table("app_devices").insert(payload).execute().data or []
        device = created[0] if created else payload
    else:
        device = rows[0]
        if device.get("authorized") or is_admin():
            try:
                payload["last_seen"] = now
                updated = client.table("app_devices").update(payload).eq("user_id", uid).eq("device_id", did).execute().data or []
                if updated:
                    device = updated[0]
            except Exception:
                pass
    return device


def audit(action: str, detail: str = ""):
    client = authenticated_client()
    user = current_user()
    if not client or not user.get("id"):
        return
    try:
        client.table("app_audit_log").insert({
            "user_id": user.get("id"),
            "email": user.get("email"),
            "action": action,
            "detail": detail or None,
            "device_id": st.session_state.get("device_id"),
        }).execute()
    except Exception:
        pass


def sign_in(email: str, password: str):
    client = _new_client()
    resp = client.auth.sign_in_with_password({"email": email.strip(), "password": password})
    user = getattr(resp, "user", None)
    if not user:
        raise PermissionError("Correo o contraseña incorrectos.")
    user_dict = {"id": str(user.id), "email": user.email}
    st.session_state["_supabase_client"] = client
    st.session_state["auth_user"] = user_dict
    try:
        _load_profile_and_permissions(client, user_dict["id"])
        device = _register_or_check_device(client, user_dict["id"])
        if not device.get("authorized", False):
            audit("login_device_pending", "Inicio desde un equipo pendiente de autorización")
            raise PermissionError("Este equipo quedó registrado, pero todavía no está autorizado. Un administrador debe habilitarlo desde Administración → Computadoras.")
        audit("login", "Inicio de sesión correcto")
        return True
    except Exception:
        # Conservamos el registro del equipo pendiente, pero cerramos la sesión local.
        try:
            client.auth.sign_out()
        except Exception:
            pass
        for k in ("_supabase_client", "auth_user", "auth_profile", "auth_permissions"):
            st.session_state.pop(k, None)
        raise



def validate_current_device(force: bool = False, max_age: int = 12):
    """Revalida periódicamente el equipo sin consultar Supabase en cada clic."""
    client = authenticated_client()
    uid = current_user().get("id")
    did = st.session_state.get("device_id") or _device_id()
    if not client or not uid:
        return False
    now_mono = time.monotonic()
    last = float(st.session_state.get("_device_checked_at", 0) or 0)
    if not force and (now_mono - last) < max_age:
        return True
    resp = client.table("app_devices").select("*").eq("user_id", uid).eq("device_id", did).limit(1).execute()
    rows = resp.data or []
    if not rows:
        device = _register_or_check_device(client, uid)
    else:
        device = rows[0]
    if not device.get("authorized", False):
        raise PermissionError("Esta computadora fue bloqueada o todavía no ha sido autorizada por un administrador.")
    try:
        client.table("app_devices").update({"last_seen": datetime.now(timezone.utc).isoformat()}).eq("user_id",uid).eq("device_id",did).execute()
    except Exception:
        pass
    st.session_state["_device_checked_at"] = now_mono
    return True

def logout():
    audit("logout", "Cierre de sesión")
    client = authenticated_client()
    try:
        if client:
            client.auth.sign_out()
    except Exception:
        pass
    for k in list(st.session_state.keys()):
        if k.startswith("auth_") or k in {"_supabase_client", "device_id", "sesion_iniciada", "_auth_checked_at", "_device_checked_at"}:
            st.session_state.pop(k, None)


def change_own_password(new_password: str):
    if len(new_password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    client = authenticated_client()
    if not client:
        raise RuntimeError("No hay sesión activa.")
    client.auth.update_user({"password": new_password})
    audit("password_changed", "El usuario cambió su contraseña")


def request_password_reset(email: str):
    client = _new_client()
    client.auth.reset_password_for_email(email.strip())


EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _clean_email(email: str) -> str:
    value = (email or "").strip().lower()
    if not EMAIL_RE.match(value):
        raise ValueError("Escribe un correo electrónico válido.")
    return value


def _validate_password(password: str):
    if len(password or "") < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    if len(password) > 72:
        raise ValueError("La contraseña no puede superar 72 caracteres.")


def create_collaborator(email: str, password: str, display_name: str):
    """Crea o repara un colaborador sin dejar perfiles incompletos.

    El alta en Auth se hace con un cliente independiente para no reemplazar la
    sesión del administrador. Después, una RPC SECURITY DEFINER finaliza de
    forma transaccional el perfil, la contraseña y los permisos iniciales.
    """
    require_permission("usuarios", "create")
    email = _clean_email(email)
    _validate_password(password)
    display_name = (display_name or "").strip() or email
    if len(display_name) > 120:
        raise ValueError("El nombre para mostrar es demasiado largo.")

    client = authenticated_client()
    if not client:
        raise RuntimeError("No hay una sesión administrativa activa.")

    # Si ya tiene perfil, no creamos duplicados silenciosos.
    existing = client.table("app_profiles").select("user_id,email,status").eq("email", email).limit(1).execute().data or []
    if existing:
        raise ValueError("Ese correo ya está registrado en Vincúlate. Puedes cambiar su contraseña o permisos desde Administración.")

    # Crear en Supabase Auth. En un usuario huérfano/duplicado Supabase puede
    # ocultar deliberadamente el detalle; la RPC de finalización localiza el
    # usuario real por correo y repara su perfil.
    signup_error = None
    try:
        public_client = _new_client()
        public_client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"display_name": display_name}},
        })
    except Exception as exc:
        signup_error = exc

    try:
        resp = client.rpc("admin_finalize_collaborator", {
            "p_email": email,
            "p_new_password": password,
            "p_display_name": display_name,
        }).execute()
    except Exception as exc:
        detail = str(exc)
        if signup_error:
            detail = f"{detail} | Alta Auth: {signup_error}"
        raise RuntimeError(
            "No se pudo finalizar el usuario. Ejecuta en Supabase el archivo "
            "supabase/04_USUARIOS_PERMISOS_ESTABLE.sql y vuelve a intentarlo. "
            f"Detalle: {detail}"
        ) from exc

    data = getattr(resp, "data", None)
    uid = None
    if isinstance(data, str):
        uid = data
    elif isinstance(data, list) and data:
        first = data[0]
        uid = str(first.get("user_id") or first.get("admin_finalize_collaborator") or "") if isinstance(first, dict) else str(first)
    elif isinstance(data, dict):
        uid = str(data.get("user_id") or data.get("admin_finalize_collaborator") or "")
    if not uid:
        # Verificación final por perfil: evita mostrar éxito sin persistencia.
        rows = client.table("app_profiles").select("user_id").eq("email", email).limit(1).execute().data or []
        uid = str(rows[0]["user_id"]) if rows else ""
    if not uid:
        raise RuntimeError("Supabase no confirmó la persistencia del nuevo colaborador.")

    audit("user_created", f"Colaborador creado/reparado: {email}")
    return uid


def save_user_permissions(uid: str, permissions: list[dict]):
    """Guarda toda la matriz y verifica que lo persistido coincida."""
    require_permission("usuarios", "edit")
    client = authenticated_client()
    if not client:
        raise RuntimeError("No hay una sesión administrativa activa.")

    normalized = []
    for row in permissions:
        mk = str(row.get("module_key", "")).strip()
        if mk not in MODULES:
            continue
        can_view = bool(row.get("can_view", False))
        normalized.append({
            "module_key": mk,
            "can_view": can_view,
            "can_create": bool(row.get("can_create", False)) and can_view,
            "can_edit": bool(row.get("can_edit", False)) and can_view,
            "can_delete": bool(row.get("can_delete", False)) and can_view,
            "can_export": bool(row.get("can_export", False)) and can_view,
        })

    try:
        client.rpc("admin_replace_user_permissions", {
            "p_user_id": uid,
            "p_permissions": normalized,
        }).execute()
    except Exception as exc:
        raise RuntimeError(
            "No se pudieron guardar los permisos de forma segura. Ejecuta "
            "supabase/04_USUARIOS_PERMISOS_ESTABLE.sql. " + str(exc)
        ) from exc

    rows = client.table("app_permissions").select("module_key,can_view,can_create,can_edit,can_delete,can_export").eq("user_id", uid).execute().data or []
    got = {r["module_key"]: tuple(bool(r.get(k)) for k in ("can_view","can_create","can_edit","can_delete","can_export")) for r in rows}
    expected = {r["module_key"]: tuple(bool(r.get(k)) for k in ("can_view","can_create","can_edit","can_delete","can_export")) for r in normalized}
    if any(got.get(k) != v for k, v in expected.items()):
        raise RuntimeError("Supabase respondió, pero la verificación de permisos no coincidió con lo solicitado.")
    return normalized


def admin_update_account(uid: str, email: str, display_name: str, role: str, status: str):
    require_permission("usuarios", "edit")
    email = _clean_email(email)
    display_name = (display_name or "").strip() or email
    if role not in {"admin", "collaborator"}:
        raise ValueError("Rol inválido.")
    if status not in {"pending", "active", "disabled"}:
        raise ValueError("Estado inválido.")
    client = authenticated_client()
    resp = client.rpc("admin_update_user_account", {
        "p_user_id": uid, "p_email": email, "p_display_name": display_name,
        "p_role": role, "p_status": status,
    }).execute()
    audit("account_updated", f"Cuenta actualizada: {email}; role={role}; status={status}")
    return getattr(resp, "data", None)


def admin_delete_account(uid: str):
    require_permission("usuarios", "delete")
    if str(uid) == str(current_user().get("id")):
        raise ValueError("No puedes dar de baja definitivamente tu propia cuenta desde una sesión activa.")
    client = authenticated_client()
    profile = client.table("app_profiles").select("email").eq("user_id", uid).limit(1).execute().data or []
    email = profile[0].get("email") if profile else uid
    client.rpc("admin_delete_user_account", {"p_user_id": uid}).execute()
    audit("account_deleted", f"Cuenta eliminada: {email}")
    return True
