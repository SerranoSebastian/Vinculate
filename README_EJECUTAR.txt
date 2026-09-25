SEDECO Modular con seguimiento de vinculación

EJECUCIÓN LOCAL CON DOBLE CLIC (WINDOWS)
----------------------------------------
1) Extraer completamente el ZIP.
2) Abrir la carpeta SEDECO_vin.
3) Ejecutar INICIAR_SEDECO.bat.

La primera ejecución crea un entorno privado e instala los componentes.
Las siguientes ejecuciones son directas y abren la aplicación en el navegador.
Usa CERRAR_SEDECO.bat para apagar el servidor local.
Consulta LEEME_PRIMERO.txt para instrucciones completas.

IDENTIDAD INSTITUCIONAL
-----------------------
- La aplicación muestra una portada de bienvenida antes del sistema.
- El botón "Iniciar sesión" solo da acceso visual; temporalmente no autentica.
- Se integraron los logotipos oficiales de Tlaxcala y SEDECO.
- La interfaz usa la paleta guinda, dorado, beige y blanco proporcionada.
- La portada utiliza una composición tipográfica centrada, sin logotipos.
- Los campos de captura son blancos con texto negro.
- Los fondos guinda utilizan texto blanco.
- Las gráficas, tablas y fondos claros utilizan etiquetas oscuras de alto contraste.

EJECUCIÓN MANUAL PARA DESARROLLO
--------------------------------
1) Abrir CMD o PowerShell en esta carpeta.

2) Instalar dependencias:
   pip install -r requirements.txt

3) Ejecutar la app:
   streamlit run app.py

Nueva sección agregada:
- 🔗 Seguimiento de Vinculación

Funciones incluidas:
- Alta de vinculación persona → empresa.
- Estatus: Pendiente, Vinculado y No vinculado.
- Una sola vinculación por persona.
- La persona se selecciona mostrando únicamente su nombre.
- Fecha de envío automática.
- Fecha de vinculación automática al cambiar el estatus a Vinculado.
- Las fechas de envío y vinculación pueden editarse manualmente.
- Selección de vacantes activas o captura directa de una vacante no registrada.
- La subsección elegida se conserva después de guardar, editar o eliminar.
- Durante cada escritura se muestra un aviso de carga.
- La interfaz incluye transiciones breves en módulos, botones, tarjetas y avisos.
- Las tablas y gráficas no usan animaciones pesadas para conservar la rapidez.
- Edición y eliminación de vinculaciones.
- Control de duplicados.
- Bases separadas: vinculados, pendientes y no vinculados.
- Estadísticas por empresa, universidad, municipio y estatus.
- Descarga de reportes en CSV.

FORMATO DE PERSONAS ACEPTADO
----------------------------
La captura manual y la carga por CSV/Excel utilizan estas columnas:
- id_persona
- nombre
- sexo
- edad (opcional)
- escolaridad
- carrera
- Institución
- id_institucion
- municipio
- id_municipio
- telefono
- correo
- grupo_prioritario
- vinculacion
- fecha_registro (opcional)

Los campos telefono, id_institucion e id_municipio se conservan como texto
para evitar que Excel elimine ceros iniciales.

Archivos principales de datos:
- data/Base de datos_Persona.csv
- data/vacantes_consolidadas_empresas.csv
- data/vinculaciones.csv
- data/personas_vinculadas.csv
- data/personas_pendientes.csv
- data/personas_no_vinculadas.csv

MÓDULO RIDET
------------
El antiguo mapa fue sustituido por "Análisis territorial RIDET".
Coloca las 12 imágenes PNG dentro de assets/ridet/ usando los nombres indicados en COLOCA_AQUI_LAS_IMAGENES.txt.
El PDF oficial ya está incluido en assets/documentos/RIDET.pdf.

ORGANIZACIÓN DE VACANTES
------------------------
- Las vacantes se pueden consultar por año, calculado automáticamente desde Fecha.
- Cada vacante tiene únicamente uno de estos estados: Activa o Finalizada.
- Las vacantes nuevas se guardan como Activa.
- El estado puede cambiarse desde Editar / eliminar.
- Los registros anteriores se conservan y se inicializan como Activa.
