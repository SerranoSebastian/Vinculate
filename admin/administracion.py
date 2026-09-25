from datetime import datetime, timezone
import pandas as pd
import streamlit as st

from utils.core import *
from utils.cloud_db import cloud_enabled, ping_cloud, count_rows as cloud_count_rows, fetch_all as cloud_fetch_all
from utils.auth import (
    authenticated_client, current_user, current_profile, has_permission,
    create_collaborator, change_own_password, save_user_permissions, admin_update_account, admin_delete_account, audit, MODULES, ACTIONS,
)


def _users_tab():
    client = authenticated_client()
    st.subheader("Usuarios y perfiles")
    if not has_permission("usuarios", "view"):
        st.info("No tienes permiso para consultar usuarios."); return

    profiles = client.table("app_profiles").select("*").order("created_at").execute().data or []
    if profiles:
        pdf = pd.DataFrame(profiles)
        st.dataframe(pdf[[c for c in ["email","display_name","role","status","created_at"] if c in pdf.columns]], use_container_width=True, hide_index=True)

    if has_permission("usuarios", "create"):
        with st.expander("➕ Dar de alta una cuenta", expanded=False):
            st.caption("El correo se normaliza a minúsculas. La contraseña temporal debe tener entre 8 y 72 caracteres.")
            with st.form("create_user"):
                name=st.text_input("Nombre para mostrar")
                email=st.text_input("Correo del colaborador")
                pw=st.text_input("Contraseña temporal", type="password")
                pw2=st.text_input("Repetir contraseña", type="password")
                go=st.form_submit_button("Crear cuenta")
            if go:
                if not name.strip(): st.error("Escribe el nombre del colaborador.")
                elif pw != pw2: st.error("Las contraseñas no coinciden.")
                else:
                    try:
                        create_collaborator(email, pw, name)
                        st.success("Cuenta creada y activa. Ahora puedes asignarle permisos."); st.rerun()
                    except Exception as e: st.error(f"No se pudo crear la cuenta: {e}")

    if not profiles:
        return
    by_label={f"{p.get('display_name') or p['email']} — {p['email']}":p for p in profiles}
    sel=st.selectbox("Administrar cuenta", list(by_label.keys()), key="profile_sel")
    row=by_label[sel]

    if has_permission("usuarios", "edit"):
        st.markdown("#### Datos, rol y acceso")
        with st.form("account_edit"):
            c1,c2=st.columns(2)
            name=c1.text_input("Nombre", value=row.get("display_name") or "")
            email=c2.text_input("Correo", value=row.get("email") or "")
            role=c1.selectbox("Rol", ["collaborator","admin"], index=1 if row.get("role")=="admin" else 0)
            statuses=["pending","active","disabled"]
            status=c2.selectbox("Estado", statuses, index=statuses.index(row.get("status")) if row.get("status") in statuses else 0)
            save=st.form_submit_button("Guardar cuenta")
        if save:
            try:
                admin_update_account(row["user_id"], email, name, role, status)
                st.success("Cuenta actualizada en Authentication y en el perfil de Vincúlate."); st.rerun()
            except Exception as e: st.error(f"No se pudo actualizar la cuenta: {e}")

        st.markdown("#### Contraseña")
        with st.form("admin_password_form"):
            newpw=st.text_input("Nueva contraseña", type="password")
            newpw2=st.text_input("Repetir nueva contraseña", type="password")
            change=st.form_submit_button("Cambiar contraseña")
        if change:
            try:
                if newpw != newpw2: raise ValueError("Las contraseñas no coinciden.")
                if len(newpw)<8 or len(newpw)>72: raise ValueError("Debe tener entre 8 y 72 caracteres.")
                client.rpc("admin_set_user_password", {"p_user_id":row["user_id"], "p_new_password":newpw}).execute()
                audit("admin_password_changed", f"Contraseña actualizada para {row.get('email')}")
                st.success("Contraseña actualizada.")
            except Exception as e: st.error(f"No se pudo cambiar la contraseña: {e}")

    if has_permission("usuarios", "delete") and str(row.get("user_id")) != str(current_user().get("id")):
        st.markdown("#### Baja definitiva")
        st.warning("La baja definitiva elimina la cuenta de Authentication, su perfil, permisos y equipos asociados. No elimina personas, vacantes ni vinculaciones.")
        confirm=st.checkbox(f"Confirmo la baja definitiva de {row.get('email')}", key=f"del_confirm_{row.get('user_id')}")
        if st.button("Dar de baja definitivamente", disabled=not confirm, key=f"del_user_{row.get('user_id')}"):
            try:
                admin_delete_account(row["user_id"])
                st.success("Cuenta dada de baja definitivamente."); st.rerun()
            except Exception as e: st.error(f"No se pudo dar de baja: {e}")


def _permissions_tab():
    client=authenticated_client()
    st.subheader("Permisos por usuario")
    if not has_permission("usuarios","edit"):
        st.info("No tienes permiso para modificar permisos."); return
    profiles=client.table("app_profiles").select("user_id,email,display_name,role,status").order("email").execute().data or []
    collaborators=[p for p in profiles if p.get("role")!="admin"]
    if not collaborators:
        st.info("No hay colaboradores."); return
    labels={f"{p.get('display_name') or p['email']} — {p['email']}":p for p in collaborators}
    key=st.selectbox("Colaborador", list(labels.keys()), key="perm_user")
    p=labels[key]; uid=p["user_id"]
    existing=client.table("app_permissions").select("*").eq("user_id",uid).execute().data or []
    emap={r["module_key"]:r for r in existing}
    rows=[]
    for mk,name in MODULES.items():
        old=emap.get(mk,{})
        rows.append({"module_key":mk,"Módulo":name,"Ver":bool(old.get("can_view")),"Crear":bool(old.get("can_create")),"Editar":bool(old.get("can_edit")),"Eliminar":bool(old.get("can_delete")),"Exportar":bool(old.get("can_export"))})
    edited=st.data_editor(pd.DataFrame(rows), hide_index=True, disabled=["module_key","Módulo"], use_container_width=True, key="perm_editor")
    if st.button("💾 Guardar permisos", type="primary"):
        payload=[]
        for _,r in edited.iterrows():
            payload.append({"user_id":uid,"module_key":r["module_key"],"can_view":bool(r["Ver"]),"can_create":bool(r["Crear"]),"can_edit":bool(r["Editar"]),"can_delete":bool(r["Eliminar"]),"can_export":bool(r["Exportar"]),"updated_at":datetime.now(timezone.utc).isoformat()})
        try:
            save_user_permissions(uid, payload)
            audit("permissions_updated",f"Permisos actualizados para {p['email']}")
            st.success("Permisos guardados y verificados en Supabase.")
        except Exception as e:
            st.error(f"No se pudieron guardar los permisos: {e}")


def _devices_tab():
    client=authenticated_client(); st.subheader("Computadoras autorizadas")
    if not has_permission("dispositivos","view"):
        st.info("No tienes permiso para consultar computadoras."); return
    devices=client.table("app_devices").select("*").order("last_seen",desc=True).execute().data or []
    if not devices: st.info("Todavía no hay equipos registrados."); return
    profiles=client.table("app_profiles").select("user_id,email,display_name").execute().data or []
    pmap={p["user_id"]:p for p in profiles}
    now=datetime.now(timezone.utc)
    view=[]
    for d in devices:
        pr=pmap.get(d.get("user_id"),{})
        last=d.get("last_seen")
        recent=False
        if last:
            try: recent=(now-datetime.fromisoformat(last.replace("Z","+00:00"))).total_seconds()<=900
            except Exception: pass
        view.append({"Usuario":pr.get("display_name") or pr.get("email") or d.get("user_id"),"Equipo":d.get("hostname"),"Sistema":d.get("os_name"),"Versión app":d.get("app_version"),"Autorizado":d.get("authorized"),"Actividad <15 min":recent,"Último acceso":last,"device_id":d.get("device_id"),"user_id":d.get("user_id")})
    df=pd.DataFrame(view)
    st.metric("Equipos autorizados", int(df["Autorizado"].sum()))
    st.metric("Con actividad reciente", int(df["Actividad <15 min"].sum()))
    st.dataframe(df.drop(columns=["device_id","user_id"]),use_container_width=True)
    if has_permission("dispositivos","edit"):
        opts={f"{r['Usuario']} | {r['Equipo']} | {str(r['device_id'])[:8]}":r for r in view}
        sk=st.selectbox("Administrar equipo",list(opts.keys()))
        r=opts[sk]
        desired=st.toggle("Equipo autorizado",value=bool(r["Autorizado"]),key="dev_auth")
        if st.button("Guardar autorización del equipo"):
            try:
                client.table("app_devices").update({"authorized":desired}).eq("user_id",r["user_id"]).eq("device_id",r["device_id"]).execute()
                audit("device_authorization_changed",f"{r['Equipo']} -> {desired}")
                st.success("Autorización actualizada."); st.rerun()
            except Exception as e: st.error(str(e))


def _priorities_tab():
    client=authenticated_client(); st.subheader("Prioridades y recordatorios")
    if not has_permission("prioridades","view"):
        st.info("No tienes permiso para ver prioridades."); return
    rows=client.table("app_priorities").select("*").order("created_at",desc=True).execute().data or []
    if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True,height=260)
    if has_permission("prioridades","create"):
        with st.form("priority_new"):
            typ=st.selectbox("Tipo",["persona","vacante","vinculacion","otro"])
            eid=st.text_input("ID o referencia")
            title=st.text_input("Título")
            desc=st.text_area("Descripción")
            level=st.selectbox("Nivel",["normal","alta","urgente"])
            d=st.date_input("Fecha del primer aviso")
            t=st.time_input("Hora del primer aviso")
            repeat=st.number_input("Repetir cada cuántos minutos",min_value=1,value=60)
            go=st.form_submit_button("Programar prioridad")
        if go:
            try:
                dt=datetime.combine(d,t).astimezone().astimezone(timezone.utc).isoformat()
                client.table("app_priorities").insert({"entity_type":typ,"entity_id":eid or "sin-id","title":title,"description":desc or None,"priority_level":level,"reminder_at":dt,"repeat_minutes":int(repeat),"active":True,"created_by":current_user()["id"]}).execute()
                audit("priority_created",title); st.success("Prioridad programada."); st.rerun()
            except Exception as e: st.error(str(e))
    active=[r for r in rows if r.get("active")]
    if active and has_permission("prioridades","edit"):
        opts={f"#{r['id']} {r.get('title')}":r for r in active}; k=st.selectbox("Prioridad activa",list(opts.keys()))
        if st.button("✓ Marcar como atendida"):
            r=opts[k]
            client.table("app_priorities").update({"active":False,"completed_at":datetime.now(timezone.utc).isoformat()}).eq("id",r["id"]).execute()
            audit("priority_completed",r.get("title") or str(r["id"])); st.success("Prioridad cerrada."); st.rerun()


def _audit_tab():
    client=authenticated_client(); st.subheader("Auditoría")
    if not has_permission("auditoria","view"):
        st.info("No tienes permiso para consultar auditoría."); return
    rows=client.table("app_audit_log").select("*").order("created_at",desc=True).limit(500).execute().data or []
    if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True,height=420)
    else: st.info("Aún no hay movimientos de auditoría.")


def _password_tab():
    st.subheader("Mi contraseña")
    with st.form("own_pw"):
        p1=st.text_input("Nueva contraseña",type="password")
        p2=st.text_input("Repetir nueva contraseña",type="password")
        go=st.form_submit_button("Cambiar mi contraseña")
    if go:
        if p1!=p2: st.error("Las contraseñas no coinciden.")
        else:
            try: change_own_password(p1); st.success("Contraseña actualizada.")
            except Exception as e: st.error(str(e))


def administracion():
    st.title("⚙️ Administración")
    ok,estado=ping_cloud() if cloud_enabled() else (False,"No configurado")
    if ok:
        try:
            n_personas=cloud_count_rows("personas")
            n_vacantes=cloud_count_rows("vacantes")
            n_seg=cloud_count_rows("vinculaciones")
        except Exception:
            n_personas=n_vacantes=n_seg=0
    else:
        # Solo en modo local se cargan los CSV completos.
        n_personas=len(cargar_personas_base())
        n_vacantes=len(cargar_vacantes_base())
        n_seg=len(cargar_vinculaciones_base())
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Vinculaciones históricas",n_personas); c2.metric("Vacantes",n_vacantes); c3.metric("Seguimientos",n_seg); c4.metric("Persistencia","Supabase ☁️" if ok else "Sin conexión")
    if ok: st.success("🟢 Conectado a la base central.")
    else: st.error(f"🔴 No se pudo validar Supabase: {estado}")

    available=[]
    for name,key in [("Usuarios","usuarios"),("Permisos","usuarios"),("Computadoras","dispositivos"),("Prioridades","prioridades"),("Auditoría","auditoria")]:
        if has_permission(key,"view") or current_profile().get("role")=="admin": available.append(name)
    available += ["Mi contraseña","Nube y respaldos"]
    tabs=st.tabs(available)
    for tab,name in zip(tabs,available):
        with tab:
            if name=="Usuarios": _users_tab()
            elif name=="Permisos": _permissions_tab()
            elif name=="Computadoras": _devices_tab()
            elif name=="Prioridades": _priorities_tab()
            elif name=="Auditoría": _audit_tab()
            elif name=="Mi contraseña": _password_tab()
            elif name=="Nube y respaldos":
                if ok and st.button("🔄 Verificar datos de nube"):
                    try: st.info(f"Nube: {cloud_count_rows('personas')} vinculaciones históricas, {cloud_count_rows('vacantes')} vacantes y {cloud_count_rows('vinculaciones')} seguimientos.")
                    except Exception as e: st.error(str(e))
                st.code(f"{PERSONAS_FILE}\n{VACANTES_FILE}\n{VINCULACIONES_FILE}\n{BACKUP_DIR}")
                try: historial=cloud_fetch_all("historial") if ok else leer_csv_seguro(HISTORIAL_FILE,HISTORIAL_COLS)
                except Exception: historial=leer_csv_seguro(HISTORIAL_FILE,HISTORIAL_COLS)
                if not historial.empty: st.dataframe(historial.sort_values("fecha_hora",ascending=False),use_container_width=True,height=280)
