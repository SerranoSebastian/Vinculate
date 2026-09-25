import streamlit as st
from pathlib import Path

from config.estilos import aplicar_estilos
from utils.core import (
    inicializar_archivos, cargar_personas_base, cargar_vacantes_base,
    preparar_personas_dashboard, explicar_visualizacion,
)
from utils.cloud_db import cloud_enabled, ping_cloud
from utils.auth import (
    sign_in, logout, is_authenticated, current_profile, current_user,
    has_permission, refresh_authorization, validate_current_device,
)
from utils.priorities import show_priority_notifications
from dashboards.personas import dashboard_personas
from dashboards.persona_detalle import consulta_persona
from dashboards.vacantes import dashboard_vacantes
from ingesta.personas import ingesta_personas
from ingesta.vacantes import ingesta_vacantes
from dashboards.explorador import explorador_general
from dashboards.ridet import modulo_ridet
from seguimiento.vinculaciones import seguimiento_vinculaciones
from admin.administracion import administracion

st.set_page_config(page_title="Sistema Integral Vincúlate SEDECO", page_icon="🏢", layout="wide")
BASE_DIR = Path(__file__).resolve().parent
LOGO_HORIZONTAL = BASE_DIR / "assets" / "identidad" / "tlaxcala_sedeco_horizontal.jpeg"

aplicar_estilos()


def login_screen():
    st.markdown("<div style='height:4vh'></div>", unsafe_allow_html=True)
    a, b, c = st.columns([1.2, 1, 1.2])
    with b:
        if LOGO_HORIZONTAL.exists():
            st.image(str(LOGO_HORIZONTAL), use_container_width=True)
        st.markdown("## VINCÚLATE")
        st.caption("Sistema Integral Vincúlate SEDECO")
        with st.form("login_form"):
            email = st.text_input("Correo electrónico")
            password = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Iniciar sesión", use_container_width=True)
        if submit:
            if not email.strip() or not password:
                st.error("Escribe tu correo y contraseña.")
            else:
                try:
                    sign_in(email, password)
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        st.caption("El acceso, los permisos y la autorización de esta computadora se validan con la base central.")


if not is_authenticated():
    login_screen()
    st.stop()

# Revalidar perfil/permisos en cada recarga para que un cambio del administrador
# se refleje sin reinstalar la aplicación.
try:
    refresh_authorization()
    validate_current_device()
except Exception as e:
    st.error(f"Tu acceso ya no está habilitado: {e}")
    if st.button("Cerrar sesión"):
        logout(); st.rerun()
    st.stop()

inicializar_archivos()
show_priority_notifications()

if LOGO_HORIZONTAL.exists():
    st.sidebar.image(str(LOGO_HORIZONTAL), use_container_width=True)
st.sidebar.title("Vincúlate SEDECO")
profile = current_profile(); user = current_user()
st.sidebar.caption(profile.get("display_name") or user.get("email") or "Usuario")
st.sidebar.caption("Administrador" if profile.get("role") == "admin" else "Colaborador")

if cloud_enabled():
    ok, _msg = ping_cloud()
    st.sidebar.caption("☁️ Base central conectada" if ok else "🔴 Nube sin conexión")

if st.sidebar.button("🔄 Actualizar permisos y datos", use_container_width=True):
    st.cache_data.clear()
    st.session_state.pop("_cloud_df_cache", None)
    st.session_state.pop("_cloud_ping", None)
    st.session_state["_auth_checked_at"] = 0
    st.session_state["_device_checked_at"] = 0
    st.rerun()
if st.sidebar.button("🚪 Cerrar sesión", use_container_width=True):
    logout(); st.rerun()

# Menú generado desde permisos SQL.
options = []
def add(label, module):
    if has_permission(module, "view"):
        options.append(label)

add("🏠 Inicio", "inicio")
add("🎓 Dashboard Personas", "personas")
add("👤 Consulta de Persona", "personas")
add("💼 Dashboard Vacantes", "vacantes")
if has_permission("personas", "create") or has_permission("personas", "edit") or has_permission("personas", "delete"):
    options.append("➕ Gestión Personas")
if has_permission("vacantes", "create") or has_permission("vacantes", "edit") or has_permission("vacantes", "delete"):
    options.append("➕ Gestión Vacantes")
add("🔗 Seguimiento de Vinculación", "vinculaciones")
add("🔎 Explorador general", "explorador")
add("🧭 Análisis territorial RIDET", "ridet")
add("⚙️ Administración", "administracion")

if not options:
    st.warning("Tu cuenta está activa, pero todavía no tiene módulos asignados. Solicita permisos a un administrador.")
    st.stop()

seccion = st.sidebar.radio("Selecciona qué quieres hacer", options)

if seccion == "🏠 Inicio":
    st.title("🏢 Sistema Integral Vincúlate SEDECO")
    st.markdown("Gestión, consulta y seguimiento de personas, empresas, vacantes y vinculaciones.")
    p = preparar_personas_dashboard(cargar_personas_base()); v = cargar_vacantes_base()
    personas_unicas = p["id_persona_maestro"].nunique() if not p.empty else 0
    vinculaciones = len(p)
    recurrentes = int((p.groupby("id_persona_maestro").size() > 1).sum()) if not p.empty else 0
    c1,c2,c3,c4=st.columns(4)
    c1.metric("👤 Personas únicas", f"{personas_unicas:,}")
    c2.metric("🔗 Vinculaciones", f"{vinculaciones:,}")
    c3.metric("🔁 Personas recurrentes", f"{recurrentes:,}")
    c4.metric("💼 Vacantes", len(v))
    explicar_visualizacion(
        "Base central de personas/vinculaciones y vacantes.",
        "Resume personas únicas, vinculaciones históricas, recurrencia y vacantes registradas.",
        "Los valores son conteos operativos de los registros disponibles en la base central."
    )
elif seccion == "🎓 Dashboard Personas": dashboard_personas()
elif seccion == "👤 Consulta de Persona": consulta_persona()
elif seccion == "💼 Dashboard Vacantes": dashboard_vacantes()
elif seccion == "➕ Gestión Personas": ingesta_personas()
elif seccion == "➕ Gestión Vacantes": ingesta_vacantes()
elif seccion == "🔗 Seguimiento de Vinculación": seguimiento_vinculaciones()
elif seccion == "🔎 Explorador general": explorador_general()
elif seccion == "🧭 Análisis territorial RIDET": modulo_ridet()
elif seccion == "⚙️ Administración": administracion()
