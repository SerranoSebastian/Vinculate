select 'personas' tabla, count(*) registros from public.personas
union all select 'vacantes', count(*) from public.vacantes
union all select 'vinculaciones', count(*) from public.vinculaciones
union all select 'historial_cargas', count(*) from public.historial_cargas;
