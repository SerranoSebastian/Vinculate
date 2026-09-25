from utils.core import *
from utils.catalogos_vacantes import EMPRESAS_SECTOR, AREAS_OPORTUNIDAD, PUESTOS_CATALOGO


def mostrar_resultado_guardado(resultado, mensaje_ok):
    if not resultado.get("ok"):
        st.error("No se guardó la información porque hay errores de validación.")
        st.dataframe(pd.DataFrame(resultado["errores"]), use_container_width=True)
        return
    st.success(
        f"{mensaje_ok} Recibidos: {resultado['recibidos']}. "
        f"Guardados nuevos: {resultado['guardados']}. "
        f"Duplicados actualizados/eliminados: {resultado['duplicados']}. "
        f"Total actual: {resultado['total']}."
    )


def _catalogo_puestos(df):
    df = limpiar_vacantes(df)
    return sorted(set(PUESTOS_CATALOGO) | {x for x in df["Tipo de Vacante"].dropna().astype(str).unique() if x.strip()})


def ingesta_vacantes():
    st.title("➕ Ingesta de Vacantes / Empresas")
    st.markdown(
        "Cada fila representa **un solo puesto**. El nombre del puesto se homologa para evitar variantes, "
        "mientras que *Puesto Original* conserva el texto capturado para trazabilidad."
    )
    df_actual = cargar_vacantes_base()
    catalogo = _catalogo_puestos(df_actual)
    vista = st.radio("Apartado", ["📝 Captura manual", "📁 Carga Excel/CSV", "✏️ Editar / eliminar", "📊 Base actual"], horizontal=True, key="vacantes_apartado", label_visibility="collapsed")

    if vista == "📝 Captura manual":
        usuario = st.text_input("Responsable de la carga", value="SEDECO", key="usuario_vacantes_manual")
        with st.form("form_vacantes"):
            c1, c2 = st.columns(2)
            with c1:
                actividad = st.text_input("Actividad", value="Publicación de vacantes")
                fecha = st.date_input("Fecha *", value=None)
                empresa = st.selectbox("Empresa *", ["Seleccionar..."] + sorted(EMPRESAS_SECTOR.keys()))
                sector = EMPRESAS_SECTOR.get(empresa, "Sin dato")
                st.text_input("Sector de la empresa", value=sector, disabled=True, help="Se asigna automáticamente con el catálogo normalizado de empresas.")
                opcion_puesto = st.selectbox("Puesto normalizado *", ["Seleccionar..."] + catalogo + ["Otro / nuevo puesto"])
                puesto_nuevo = st.text_input("Nuevo puesto", disabled=opcion_puesto != "Otro / nuevo puesto")
                tipo_oportunidad = st.selectbox("Tipo de oportunidad *", TIPOS_OPORTUNIDAD)
                area = st.selectbox("Área de oportunidad", AREAS_OPORTUNIDAD, help="Selecciona el área funcional donde se desempeñará la vacante. El catálogo evita variantes de escritura.")
            with c2:
                descripcion = st.text_area("Descripción / funciones", help="Describe qué hará la persona en el puesto: actividades, responsabilidades, procesos, equipos o tareas principales. Evita colocar aquí escolaridad, experiencia o prestaciones.")
                requisitos = st.text_area("Requisitos", help="Captura lo necesario para ocupar el puesto: escolaridad, experiencia, conocimientos, certificaciones, habilidades, disponibilidad, licencias o idiomas.")
                beneficios = st.text_area("Beneficios", help="Captura lo que ofrece la empresa: sueldo, prestaciones, bonos, transporte, comedor, vales, fondo de ahorro, seguro, capacitación u otros apoyos.")
                link = st.text_input("Link de la Publicación")
                estado = st.selectbox("Estado", ESTADOS_VACANTE)
            enviar = st.form_submit_button("Guardar vacante")
        if enviar:
            tipo = puesto_nuevo.strip() if opcion_puesto == "Otro / nuevo puesto" else opcion_puesto
            if empresa == "Seleccionar...":
                st.error("Selecciona una empresa del catálogo.")
            elif tipo == "Seleccionar...":
                st.error("Selecciona un puesto o captura uno nuevo.")
            else:
                tipo_norm = normalizar_puesto_vacante(tipo)
                nuevo = pd.DataFrame([{
                    "ID Vacante": "", "ID Registro Origen": "",
                    "Actividad": actividad, "Fecha": fecha, "Empresa": empresa, "Sector Empresa": sector,
                    "Puesto Original": tipo, "Tipo de Vacante": tipo_norm,
                    "Categoría de Puesto": categoria_puesto_vacante(tipo_norm, tipo_oportunidad),
                    "Tipo de Oportunidad": tipo_oportunidad, "Área de Oportunidad": area,
                    "Descripción": descripcion, "Requisitos": requisitos,
                    "Beneficios": beneficios, "Link de la Publicación": link, "Estado": estado
                }])
                resultado = insertar_y_guardar(df_actual, nuevo, "vacantes", usuario=usuario, origen="manual", archivo_origen="Captura manual")
                mostrar_resultado_guardado(resultado, "Registro de vacante procesado.")

    if vista == "📁 Carga Excel/CSV":
        st.subheader("Plantillas descargables")
        st.caption("En cargas masivas, registra un puesto por fila. Si una publicación contiene tres puestos, deben ser tres filas.")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("⬇️ Plantilla vacantes CSV", pd.DataFrame(columns=VACANTES_COLS).to_csv(index=False).encode("utf-8-sig"), "plantilla_vacantes.csv", "text/csv")
        with c2:
            st.download_button("⬇️ Plantilla vacantes Excel", crear_excel_plantilla(VACANTES_COLS), "plantilla_vacantes.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        usuario = st.text_input("Responsable de la carga", value="SEDECO", key="usuario_vacantes_archivo")
        archivo = st.file_uploader("Sube un archivo de vacantes (.csv, .xlsx, .xls)", type=["csv", "xlsx", "xls"])
        if archivo:
            try:
                nuevo = leer_archivo_subido(archivo)
                st.write("Vista previa del archivo:")
                st.dataframe(nuevo.head(20), use_container_width=True)
                # Se permiten archivos del esquema anterior; limpiar_vacantes crea las nuevas columnas.
                errores = validar_vacantes(nuevo)
                if errores:
                    st.error("El archivo tiene errores. Corrígelos antes de integrarlo.")
                    st.dataframe(pd.DataFrame(errores), use_container_width=True)
                elif st.button("Integrar archivo a base de vacantes"):
                    resultado = insertar_y_guardar(df_actual, nuevo, "vacantes", usuario=usuario, origen="archivo", archivo_origen=archivo.name)
                    mostrar_resultado_guardado(resultado, "Archivo de vacantes integrado.")
            except Exception as e:
                st.error(f"No se pudo leer el archivo: {e}")

    if vista == "✏️ Editar / eliminar":
        st.subheader("Editar o eliminar registros de vacantes")
        df_edit = limpiar_vacantes(df_actual).reset_index(drop=True)
        if df_edit.empty:
            st.info("No hay registros para editar.")
        else:
            opciones = [f"{i} | {r['ID Vacante']} | {r['Fecha'].date() if pd.notna(r['Fecha']) else 'Sin fecha'} | {r['Empresa']} | {r['Tipo de Vacante']}" for i, r in df_edit.iterrows()]
            seleccion = st.selectbox("Selecciona una vacante", opciones, key="sel_vacante_editar")
            idx = int(seleccion.split(" | ")[0])
            usuario = st.text_input("Responsable del cambio", value="SEDECO", key="usuario_vacantes_editar")
            fila = df_edit.loc[idx].copy()
            with st.form("editar_vacante"):
                st.caption(f"ID: {fila['ID Vacante']} · Origen: {fila['ID Registro Origen']} · Texto original: {fila['Puesto Original'] or 'Sin dato'}")
                c1, c2 = st.columns(2)
                with c1:
                    actividad = st.text_input("Actividad", value=str(fila["Actividad"]))
                    fecha_val = pd.to_datetime(fila["Fecha"], errors="coerce")
                    fecha = st.date_input("Fecha *", value=None if pd.isna(fecha_val) else fecha_val.date())
                    empresas_opts = sorted(set(EMPRESAS_SECTOR.keys()) | {str(fila["Empresa"])})
                    empresa = st.selectbox("Empresa *", empresas_opts, index=empresas_opts.index(str(fila["Empresa"])))
                    sector = EMPRESAS_SECTOR.get(empresa, str(fila.get("Sector Empresa", "Sin dato")) or "Sin dato")
                    st.text_input("Sector de la empresa", value=sector, disabled=True)
                    opciones_p = sorted(set(catalogo + [str(fila["Tipo de Vacante"])]))
                    tipo = st.selectbox("Puesto normalizado *", opciones_p, index=opciones_p.index(str(fila["Tipo de Vacante"])))
                    tipo_oportunidad = st.selectbox("Tipo de oportunidad", TIPOS_OPORTUNIDAD, index=TIPOS_OPORTUNIDAD.index(fila["Tipo de Oportunidad"]) if fila["Tipo de Oportunidad"] in TIPOS_OPORTUNIDAD else 0)
                    areas_opts = list(dict.fromkeys(AREAS_OPORTUNIDAD + ([str(fila["Área de Oportunidad"])] if str(fila["Área de Oportunidad"]) else [])))
                    area = st.selectbox("Área de oportunidad", areas_opts, index=areas_opts.index(str(fila["Área de Oportunidad"])) if str(fila["Área de Oportunidad"]) in areas_opts else 0)
                with c2:
                    descripcion = st.text_area("Descripción / funciones", value=str(fila["Descripción"]), help="Actividades, responsabilidades, procesos, equipos o tareas principales del puesto.")
                    requisitos = st.text_area("Requisitos", value=str(fila["Requisitos"]), help="Escolaridad, experiencia, conocimientos, certificaciones, habilidades, disponibilidad, licencias o idiomas.")
                    beneficios = st.text_area("Beneficios", value=str(fila["Beneficios"]), help="Sueldo, prestaciones, bonos, transporte, comedor, vales, fondo de ahorro, seguro, capacitación u otros apoyos.")
                    link = st.text_input("Link de la Publicación", value=str(fila["Link de la Publicación"]))
                    estado = st.selectbox("Estado", ESTADOS_VACANTE, index=ESTADOS_VACANTE.index(fila["Estado"]) if fila["Estado"] in ESTADOS_VACANTE else 0)
                guardar = st.form_submit_button("Guardar cambios")
            eliminar = st.button("🗑️ Eliminar esta vacante", key="eliminar_vacante")
            if guardar:
                df_edit.loc[idx, "Actividad"] = actividad
                df_edit.loc[idx, "Fecha"] = fecha
                df_edit.loc[idx, "Empresa"] = empresa
                df_edit.loc[idx, "Sector Empresa"] = sector
                df_edit.loc[idx, "Tipo de Vacante"] = normalizar_puesto_vacante(tipo)
                df_edit.loc[idx, "Categoría de Puesto"] = categoria_puesto_vacante(tipo, tipo_oportunidad)
                df_edit.loc[idx, "Tipo de Oportunidad"] = tipo_oportunidad
                df_edit.loc[idx, "Área de Oportunidad"] = area
                df_edit.loc[idx, "Descripción"] = descripcion
                df_edit.loc[idx, "Requisitos"] = requisitos
                df_edit.loc[idx, "Beneficios"] = beneficios
                df_edit.loc[idx, "Link de la Publicación"] = link
                df_edit.loc[idx, "Estado"] = estado
                resultado = guardar_registro_editado("vacantes", df_edit.loc[[idx], VACANTES_COLS], usuario=usuario, accion="edición")
                if resultado.get("ok"):
                    st.success(f"Vacante actualizada. Total actual: {resultado['total']}.")
                else:
                    st.error("No se pudo guardar por errores de validación.")
                    st.dataframe(pd.DataFrame(resultado["errores"]), use_container_width=True)
            if eliminar:
                resultado = eliminar_registro("vacantes", fila["ID Vacante"], usuario=usuario, accion="eliminación")
                if resultado.get("ok"):
                    st.success(f"Vacante eliminada. Total actual: {resultado['total']}.")

    if vista == "📊 Base actual":
        df_listado = preparar_vacantes_dashboard(df_actual)
        años_disponibles = sorted(df_listado["Año"].dropna().astype(int).unique().tolist(), reverse=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            año_seleccionado = st.selectbox("Año", ["Todos"] + años_disponibles, key="listado_vacantes_anio")
        with c2:
            estado_seleccionado = st.selectbox("Estado", ["Todas"] + ESTADOS_VACANTE, key="listado_vacantes_estado")
        with c3:
            oportunidad = st.selectbox("Tipo de oportunidad", ["Todas"] + TIPOS_OPORTUNIDAD, key="listado_vacantes_oportunidad")
        if año_seleccionado != "Todos": df_listado = df_listado[df_listado["Año"] == int(año_seleccionado)]
        if estado_seleccionado != "Todas": df_listado = df_listado[df_listado["Estado"] == estado_seleccionado]
        if oportunidad != "Todas": df_listado = df_listado[df_listado["Tipo de Oportunidad"] == oportunidad]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Puestos mostrados", len(df_listado))
        c2.metric("Activas", int(df_listado["Estado"].eq("Activa").sum()))
        c3.metric("Empresas", df_listado["Empresa"].nunique())
        c4.metric("Puestos distintos", df_listado["Tipo de Vacante"].nunique())
        explicar_visualizacion("Base actual de vacantes después de los filtros de año, estado y tipo de oportunidad.", "Resume registros mostrados, vacantes activas, empresas únicas y puestos distintos.", "Sirve como control de la base: los conteos cambian con los filtros y representan registros disponibles, no contrataciones.")
        st.dataframe(df_listado, use_container_width=True, height=500)
        st.download_button("⬇️ Descargar listado filtrado", df_listado.to_csv(index=False).encode("utf-8-sig"), "vacantes_filtradas_por_anio_estado.csv", "text/csv")
