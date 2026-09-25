from utils.core import *

def explorador_general():
    st.title("🔎 Explorador general")
    base = st.radio("Selecciona la base", ["Personas", "Vacantes"], horizontal=True)
    df = preparar_personas_dashboard(cargar_personas_base()) if base == "Personas" else preparar_vacantes_dashboard(cargar_vacantes_base())
    busqueda = st.text_input("Buscar en toda la tabla")
    df_b = df.copy()
    if busqueda:
        texto = busqueda.lower()
        df_b = df_b[df_b.astype(str).apply(lambda fila: fila.str.lower().str.contains(texto, na=False).any(), axis=1)]
    st.metric("Registros encontrados", len(df_b))
    explicar_visualizacion(f"Base seleccionada: {base}, después de aplicar la búsqueda de texto.", "Cuenta las filas que coinciden con el criterio actual.", "Un valor menor que el total indica que la búsqueda está acotando resultados; no representa personas únicas salvo que la base y el análisis lo definan así.")
    st.dataframe(df_b, use_container_width=True, height=560)
    st.download_button("⬇️ Descargar resultado", df_b.to_csv(index=False).encode("utf-8-sig"), f"{base.lower()}_explorador.csv", "text/csv")


