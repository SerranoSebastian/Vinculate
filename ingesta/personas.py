from utils.core import *
from utils.catalogos_academicos import (
    ESCOLARIDADES, GRUPOS_PRIORITARIOS, catalogo_instituciones, catalogo_carreras,
    catalogo_areas, opcion_canonica, escolaridad_canonica, grupo_canonico
)


def mostrar_resultado_guardado(resultado, mensaje_ok):
    if not resultado.get("ok"):
        st.error("No se guardó la información porque hay errores de validación.")
        st.dataframe(pd.DataFrame(resultado["errores"]), use_container_width=True)
        return
    st.success(
        f"{mensaje_ok} Recibidos: {resultado['recibidos']}. Guardados: {resultado['guardados']}. "
        f"IDs de registro actualizados: {resultado['duplicados']}. Total de vinculaciones históricas: {resultado['total']}."
    )


def _valor_base(persona, campo, default=""):
    if persona is None:
        return default
    v = persona.get(campo, default)
    return default if pd.isna(v) else str(v)


def ingesta_personas():
    st.title("➕ Registro de Personas y Vinculaciones")
    st.markdown("""
    <style>
    div[data-testid="stFormSubmitButton"] > button {
        min-height: 3rem; border-radius: 12px; font-weight: 700; font-size: 1rem;
        box-shadow: 0 4px 12px rgba(91, 18, 43, .18);
    }
    </style>
    """, unsafe_allow_html=True)
    st.markdown(
        "Cada captura agrega una **vinculación histórica**. Si la persona ya existe, se conserva su `id_persona_maestro`; "
        "si es nueva, el sistema genera uno. El `id_persona` identifica únicamente ese registro de vinculación."
    )
    df_actual = limpiar_personas(cargar_personas_base())
    maestras = obtener_personas_maestras(df_actual)
    instituciones_catalogo = catalogo_instituciones(df_actual)
    carreras_catalogo = catalogo_carreras(df_actual)
    areas_catalogo = catalogo_areas(df_actual)

    if st.session_state.pop("persona_guardada_ok", False):
        id_guardado = st.session_state.pop("persona_guardada_id", "")
        maestro_guardado = st.session_state.pop("persona_guardada_maestro", "")
        st.success(f"✅ Información guardada correctamente. Vinculación {id_guardado} asociada a {maestro_guardado}.")
    vista = st.radio("Apartado", ["📝 Nueva vinculación", "📁 Carga Excel/CSV", "✏️ Editar / eliminar", "📊 Base actual"], horizontal=True, key="personas_apartado", label_visibility="collapsed")

    if vista == "📝 Nueva vinculación":
        usuario = st.text_input("Responsable de la carga", value="SEDECO", key="usuario_personas_manual")
        modo = st.radio("¿La persona ya existe?", ["Sí, asociar a persona existente", "No, crear persona nueva"], horizontal=True)
        persona_ref = None
        if modo.startswith("Sí"):
            if maestras.empty:
                st.info("Todavía no existen personas maestras. Registra una persona nueva.")
            else:
                indices = list(maestras.index)
                idx = st.selectbox(
                    "Persona maestra",
                    indices,
                    format_func=lambda i: f"{maestras.loc[i, 'nombre']} — {maestras.loc[i, 'id_persona_maestro']} — {int(maestras.loc[i, 'total_vinculaciones'])} vinculaciones",
                    key="persona_maestra_captura",
                )
                persona_ref = maestras.loc[idx]
                st.caption(f"La nueva vinculación quedará asociada a {persona_ref['id_persona_maestro']}.")

        tipo = st.selectbox("Tipo de vinculación *", TIPOS_VINCULACION, key="tipo_vinc_nueva")
        id_registro_preview = generar_id_registro_vinculacion(df_actual, tipo)
        id_maestro_preview = persona_ref["id_persona_maestro"] if persona_ref is not None else generar_id_persona_maestro(df_actual)
        cprev1, cprev2 = st.columns(2)
        cprev1.text_input("ID persona maestra", value=str(id_maestro_preview), disabled=True)
        cprev2.text_input("ID vinculación histórica", value=id_registro_preview, disabled=True)

        with st.form("form_personas_maestro"):
            c1, c2, c3 = st.columns(3)
            with c1:
                nombre = st.text_input("Nombre *", value=_valor_base(persona_ref, "nombre"))
                sexo_opts = ["", "Femenino", "Masculino", "Indefinido"]
                sexo_actual = _valor_base(persona_ref, "sexo")
                sexo_index = sexo_opts.index(sexo_actual) if sexo_actual in sexo_opts else 0
                sexo = st.selectbox("Sexo", sexo_opts, index=sexo_index, format_func=lambda x: "Vacío" if x == "" else x)
                edad_actual = pd.to_numeric(persona_ref.get("edad"), errors="coerce") if persona_ref is not None else None
                edad = st.number_input("Edad (0 = sin dato)", min_value=0, max_value=120, value=int(edad_actual) if pd.notna(edad_actual) else 0)
                telefono = st.text_input("Teléfono", value=_valor_base(persona_ref, "telefono"))
            with c2:
                esc_actual = escolaridad_canonica(_valor_base(persona_ref, "escolaridad"))
                escolaridad = st.selectbox("Escolaridad", ESCOLARIDADES, index=ESCOLARIDADES.index(esc_actual))
                car_actual = opcion_canonica(_valor_base(persona_ref, "carrera"), carreras_catalogo, "Indefinido")
                carrera = st.selectbox("Carrera", carreras_catalogo, index=carreras_catalogo.index(car_actual), help="Catálogo centralizado: las carreras equivalentes se muestran una sola vez.")
                inst_actual = opcion_canonica(_valor_base(persona_ref, "Institución"), instituciones_catalogo, "Indefinido")
                institucion = st.selectbox("Institución", instituciones_catalogo, index=instituciones_catalogo.index(inst_actual), help="Incluye las instituciones ya normalizadas y un catálogo ampliado; no admite texto libre.")
                id_institucion = st.text_input("ID institución", value=_valor_base(persona_ref, "id_institucion"))
                correo = st.text_input("Correo", value=_valor_base(persona_ref, "correo"))
            with c3:
                ubicacion_actual = normalizar_ubicacion_mexico(_valor_base(persona_ref, "municipio"))
                ubicacion_opts = opciones_ubicacion(ubicacion_actual)
                ubicacion_idx = ubicacion_opts.index(ubicacion_actual) if ubicacion_actual in ubicacion_opts else 0
                municipio = st.selectbox(
                    "Municipio de Tlaxcala / estado",
                    ubicacion_opts,
                    index=ubicacion_idx,
                    format_func=lambda x: "Sin dato" if x == "" else x,
                    help="Para Tlaxcala selecciona uno de sus 60 municipios. Para una persona de otra entidad selecciona el estado correspondiente.",
                )
                id_municipio = st.text_input("ID municipio", value=_valor_base(persona_ref, "id_municipio"))
                grupo_actual = grupo_canonico(_valor_base(persona_ref, "grupo_prioritario"), edad_actual)
                grupo_prioritario = st.selectbox("Grupo prioritario", GRUPOS_PRIORITARIOS, index=GRUPOS_PRIORITARIOS.index(grupo_actual))
                area_actual = opcion_canonica(_valor_base(persona_ref, "area_carrera"), areas_catalogo, "Indefinido")
                area_carrera = st.selectbox("Área de carrera", areas_catalogo, index=areas_catalogo.index(area_actual))
                fecha_registro = st.date_input("Fecha de registro (opcional)", value=None)
            enviar = st.form_submit_button("💾 Guardar información y vinculación", use_container_width=True)

        if enviar:
            nuevo = pd.DataFrame([{
                "id_persona": id_registro_preview,
                "id_persona_maestro": id_maestro_preview,
                "nombre": nombre,
                "sexo": sexo,
                "edad": None if edad == 0 else edad,
                "escolaridad": escolaridad,
                "carrera": carrera,
                "Institución": institucion,
                "id_institucion": id_institucion,
                "municipio": municipio,
                "id_municipio": id_municipio,
                "telefono": telefono,
                "correo": correo,
                "grupo_prioritario": grupo_prioritario,
                "vinculacion": tipo,
                "fecha_registro": fecha_registro,
                "Año": fecha_registro.year if fecha_registro else "",
                "area_carrera": area_carrera,
                "estatus_vinculacion": "Vinculado",
            }])
            resultado = insertar_y_guardar(df_actual, nuevo, "personas", usuario=usuario, origen="manual", archivo_origen="Captura manual")
            if resultado.get("ok"):
                st.session_state["persona_guardada_ok"] = True
                st.session_state["persona_guardada_id"] = id_registro_preview
                st.session_state["persona_guardada_maestro"] = id_maestro_preview
                st.rerun()
            else:
                mostrar_resultado_guardado(resultado, f"Vinculación {id_registro_preview} asociada a {id_maestro_preview}.")

    if vista == "📁 Carga Excel/CSV":
        st.subheader("Plantillas descargables")
        st.caption("Para conservar asociaciones entre registros, incluye siempre `id_persona_maestro` cuando importes históricos ya normalizados.")
        c1, c2 = st.columns(2)
        c1.download_button("⬇️ Plantilla CSV", pd.DataFrame(columns=PERSONAS_COLS).to_csv(index=False).encode("utf-8-sig"), "plantilla_personas_vinculaciones.csv", "text/csv")
        c2.download_button("⬇️ Plantilla Excel", crear_excel_plantilla(PERSONAS_COLS), "plantilla_personas_vinculaciones.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        usuario = st.text_input("Responsable de la carga", value="SEDECO", key="usuario_personas_archivo")
        archivo = st.file_uploader("Sube un archivo (.csv, .xlsx, .xls)", type=["csv", "xlsx", "xls"])
        if archivo:
            try:
                nuevo_raw = leer_archivo_subido(archivo)
                st.write("Vista previa:")
                st.dataframe(nuevo_raw.head(20), use_container_width=True)
                tiene_maestro = any(c.strip().lower() == "id_persona_maestro" for c in nuevo_raw.columns)
                if not tiene_maestro:
                    st.warning("El archivo no contiene `id_persona_maestro`. El sistema generará IDs nuevos; no podrá inferir con seguridad qué filas pertenecen a la misma persona.")
                errores = validar_personas(nuevo_raw)
                if errores:
                    st.error("El archivo tiene errores de validación.")
                    st.dataframe(pd.DataFrame(errores), use_container_width=True)
                elif st.button("Integrar archivo a la base"):
                    resultado = insertar_y_guardar(df_actual, nuevo_raw, "personas", usuario=usuario, origen="archivo", archivo_origen=archivo.name)
                    mostrar_resultado_guardado(resultado, "Archivo integrado.")
                    if resultado.get("ok"): st.rerun()
            except Exception as e:
                st.error(f"No se pudo leer el archivo: {e}")

    if vista == "✏️ Editar / eliminar":
        st.subheader("Editar o eliminar una vinculación histórica")
        df_edit = limpiar_personas(df_actual).reset_index(drop=True)
        if df_edit.empty:
            st.info("No hay registros para editar.")
        else:
            opciones = list(df_edit.index)
            idx = st.selectbox(
                "Registro",
                opciones,
                format_func=lambda i: f"{df_edit.loc[i, 'id_persona']} | {df_edit.loc[i, 'nombre']} | {df_edit.loc[i, 'id_persona_maestro']} | {df_edit.loc[i, 'vinculacion']}",
                key="sel_persona_editar",
            )
            fila = df_edit.loc[idx].copy(); usuario = st.text_input("Responsable del cambio", value="SEDECO", key="usuario_personas_editar")
            with st.form("editar_persona"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.text_input("ID vinculación histórica", value=str(fila["id_persona"]), disabled=True)
                    id_maestro = st.text_input("ID persona maestra", value=str(fila["id_persona_maestro"]))
                    nombre = st.text_input("Nombre *", value=str(fila["nombre"]))
                    sexo = st.text_input("Sexo", value=str(fila["sexo"]))
                    edad = st.number_input("Edad (0 = sin dato)", min_value=0, max_value=120, value=int(fila["edad"]) if pd.notna(fila["edad"]) else 0)
                    telefono = st.text_input("Teléfono", value=str(fila["telefono"]))
                with c2:
                    esc_edit = escolaridad_canonica(fila["escolaridad"])
                    escolaridad = st.selectbox("Escolaridad", ESCOLARIDADES, index=ESCOLARIDADES.index(esc_edit), key=f"esc_edit_{fila['id_persona']}")
                    car_edit = opcion_canonica(fila["carrera"], carreras_catalogo, "Indefinido")
                    carrera = st.selectbox("Carrera", carreras_catalogo, index=carreras_catalogo.index(car_edit), key=f"car_edit_{fila['id_persona']}")
                    inst_edit = opcion_canonica(fila["Institución"], instituciones_catalogo, "Indefinido")
                    institucion = st.selectbox("Institución", instituciones_catalogo, index=instituciones_catalogo.index(inst_edit), key=f"inst_edit_{fila['id_persona']}")
                    id_institucion = st.text_input("ID institución", value=str(fila["id_institucion"]))
                    correo = st.text_input("Correo", value=str(fila["correo"]))
                    area_edit = opcion_canonica(fila["area_carrera"], areas_catalogo, "Indefinido")
                    area_carrera = st.selectbox("Área de carrera", areas_catalogo, index=areas_catalogo.index(area_edit), key=f"area_edit_{fila['id_persona']}")
                with c3:
                    ubicacion_actual = normalizar_ubicacion_mexico(fila["municipio"])
                    ubicacion_opts = opciones_ubicacion(ubicacion_actual)
                    ubicacion_idx = ubicacion_opts.index(ubicacion_actual) if ubicacion_actual in ubicacion_opts else 0
                    municipio = st.selectbox(
                        "Municipio de Tlaxcala / estado",
                        ubicacion_opts,
                        index=ubicacion_idx,
                        format_func=lambda x: "Sin dato" if x == "" else x,
                        help="El catálogo evita variantes de escritura. Tlaxcala se registra por municipio y el resto del país por estado.",
                        key=f"ubicacion_editar_{fila['id_persona']}",
                    )
                    id_municipio = st.text_input("ID municipio", value=str(fila["id_municipio"]))
                    grupo_edit = grupo_canonico(fila["grupo_prioritario"], fila["edad"])
                    grupo = st.selectbox("Grupo prioritario", GRUPOS_PRIORITARIOS, index=GRUPOS_PRIORITARIOS.index(grupo_edit), key=f"grupo_edit_{fila['id_persona']}")
                    tipo = st.selectbox("Tipo de vinculación", TIPOS_VINCULACION, index=TIPOS_VINCULACION.index(fila["vinculacion"]) if fila["vinculacion"] in TIPOS_VINCULACION else 0)
                    fecha_val = pd.to_datetime(fila["fecha_registro"], errors="coerce")
                    fecha = st.date_input("Fecha", value=None if pd.isna(fecha_val) else fecha_val.date())
                guardar = st.form_submit_button("💾 Guardar cambios", use_container_width=True)
            eliminar = st.button("🗑️ Eliminar esta vinculación histórica", key=f"eliminar_persona_{fila['id_persona']}")
            if guardar:
                df_edit.loc[idx, PERSONAS_COLS] = [
                    fila["id_persona"], id_maestro, nombre, sexo, None if edad == 0 else edad,
                    escolaridad, carrera, institucion, id_institucion, municipio, id_municipio,
                    telefono, correo, grupo, tipo, fecha, fecha.year if fecha else "", area_carrera, "Vinculado"
                ]
                resultado = guardar_registro_editado("personas", df_edit.loc[[idx], PERSONAS_COLS], usuario=usuario, accion="edición")
                if resultado.get("ok"): st.success("Registro actualizado."); st.rerun()
                else: st.dataframe(pd.DataFrame(resultado["errores"]), use_container_width=True)
            if eliminar:
                resultado = eliminar_registro("personas", fila["id_persona"], usuario=usuario, accion="eliminación")
                if resultado.get("ok"): st.success("Vinculación histórica eliminada."); st.rerun()

    if vista == "📊 Base actual":
        c1, c2, c3 = st.columns(3)
        c1.metric("Personas únicas", df_actual["id_persona_maestro"].nunique())
        c2.metric("Vinculaciones históricas", len(df_actual))
        c3.metric("Personas con 2+ vinculaciones", int((df_actual.groupby("id_persona_maestro").size() > 1).sum()))
        explicar_visualizacion("Base actual de personas cargada desde data/Base de datos_Persona.csv.", "Resume personas únicas, vinculaciones históricas y personas recurrentes.", "Permite comprobar el tamaño de la base después de altas/ediciones; las personas recurrentes tienen dos o más vinculaciones históricas.")
        st.success("Todos los registros históricos se consideran actualmente **Vinculados**. Empresa y detalles se completan desde edición/seguimiento.")
        st.dataframe(preparar_personas_dashboard(df_actual), use_container_width=True, height=520)
        st.download_button("⬇️ Descargar base actual", df_actual.to_csv(index=False).encode("utf-8-sig"), "Base_personas_vinculaciones_actualizada.csv", "text/csv")
