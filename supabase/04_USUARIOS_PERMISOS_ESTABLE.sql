-- VINCÚLATE SEDECO — estabilización de usuarios, contraseñas y permisos
-- Fecha: 2026-09-14
-- Ejecutar UNA VEZ en Supabase > SQL Editor, en el mismo proyecto de Vincúlate.
-- Este script NO elimina personas, vacantes ni vinculaciones.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Evita permisos duplicados si la tabla ya existe con el esquema esperado.
CREATE UNIQUE INDEX IF NOT EXISTS app_permissions_user_module_uidx
ON public.app_permissions(user_id, module_key);

-- Finaliza o repara un colaborador ya creado en Supabase Authentication.
-- La aplicación primero solicita el alta a Auth; esta función localiza el
-- usuario real por correo y completa su perfil de Vincúlate de forma atómica.
CREATE OR REPLACE FUNCTION public.admin_finalize_collaborator(
  p_email text,
  p_new_password text,
  p_display_name text
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth, extensions
AS $$
DECLARE
  v_email text := lower(trim(coalesce(p_email,'')));
  v_uid uuid;
  v_name text := trim(coalesce(p_display_name,''));
BEGIN
  IF NOT (public.is_admin() OR public.has_permission('usuarios','create')) THEN
    RAISE EXCEPTION 'No autorizado para crear usuarios';
  END IF;

  IF v_email = '' OR position('@' in v_email) <= 1 THEN
    RAISE EXCEPTION 'Correo electrónico inválido';
  END IF;

  IF p_new_password IS NULL OR length(p_new_password) < 8 OR length(p_new_password) > 72 THEN
    RAISE EXCEPTION 'La contraseña debe tener entre 8 y 72 caracteres';
  END IF;

  SELECT id INTO v_uid
  FROM auth.users
  WHERE lower(email) = v_email
  ORDER BY created_at DESC
  LIMIT 1;

  IF v_uid IS NULL THEN
    RAISE EXCEPTION 'El usuario todavía no existe en Supabase Authentication. Reintenta el alta.';
  END IF;

  IF v_name = '' THEN
    v_name := v_email;
  END IF;

  -- Contraseña temporal y confirmación del correo para el uso interno de la app.
  UPDATE auth.users
  SET encrypted_password = crypt(p_new_password, gen_salt('bf')),
      email_confirmed_at = coalesce(email_confirmed_at, now()),
      raw_user_meta_data = coalesce(raw_user_meta_data, '{}'::jsonb) || jsonb_build_object('display_name', v_name),
      updated_at = now()
  WHERE id = v_uid;

  INSERT INTO public.app_profiles(user_id,email,display_name,role,status)
  VALUES (v_uid,v_email,v_name,'collaborator','active')
  ON CONFLICT (user_id) DO UPDATE
  SET email = EXCLUDED.email,
      display_name = EXCLUDED.display_name,
      role = CASE WHEN public.app_profiles.role = 'admin' THEN 'admin' ELSE 'collaborator' END,
      status = 'active';

  -- Si existía un perfil huérfano con el mismo correo y otro UUID, se detiene
  -- antes de crear inconsistencias silenciosas.
  IF EXISTS (
    SELECT 1 FROM public.app_profiles
    WHERE lower(email)=v_email AND user_id<>v_uid
  ) THEN
    RAISE EXCEPTION 'Existe un perfil duplicado con este correo. Requiere limpieza administrativa.';
  END IF;

  -- Matriz inicial completa. Inicio visible; el resto sin permiso.
  INSERT INTO public.app_permissions(user_id,module_key,can_view,can_create,can_edit,can_delete,can_export,updated_at)
  SELECT v_uid, m.module_key,
         (m.module_key='inicio'), false, false, false, false, now()
  FROM (VALUES
      ('inicio'),('personas'),('vacantes'),('vinculaciones'),('explorador'),
      ('ridet'),('administracion'),('usuarios'),('dispositivos'),
      ('prioridades'),('auditoria'),('respaldos')
  ) AS m(module_key)
  ON CONFLICT (user_id,module_key) DO NOTHING;

  RETURN v_uid;
END;
$$;

REVOKE ALL ON FUNCTION public.admin_finalize_collaborator(text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_finalize_collaborator(text,text,text) TO authenticated;


-- Reemplaza toda la matriz de permisos del colaborador en una sola transacción.
-- Si Ver=false, las demás acciones se fuerzan a false para evitar combinaciones
-- incoherentes como Editar=true con Ver=false.
CREATE OR REPLACE FUNCTION public.admin_replace_user_permissions(
  p_user_id uuid,
  p_permissions jsonb
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  item jsonb;
  mk text;
  cv boolean;
BEGIN
  IF NOT (public.is_admin() OR public.has_permission('usuarios','edit')) THEN
    RAISE EXCEPTION 'No autorizado para modificar permisos';
  END IF;

  IF NOT EXISTS (SELECT 1 FROM public.app_profiles WHERE user_id=p_user_id) THEN
    RAISE EXCEPTION 'El perfil indicado no existe';
  END IF;

  IF EXISTS (SELECT 1 FROM public.app_profiles WHERE user_id=p_user_id AND role='admin') THEN
    RAISE EXCEPTION 'La matriz de un administrador no se modifica desde esta operación';
  END IF;

  IF jsonb_typeof(p_permissions) <> 'array' THEN
    RAISE EXCEPTION 'Formato de permisos inválido';
  END IF;

  DELETE FROM public.app_permissions WHERE user_id=p_user_id;

  FOR item IN SELECT value FROM jsonb_array_elements(p_permissions)
  LOOP
    mk := trim(coalesce(item->>'module_key',''));
    IF mk NOT IN ('inicio','personas','vacantes','vinculaciones','explorador','ridet','administracion','usuarios','dispositivos','prioridades','auditoria','respaldos') THEN
      CONTINUE;
    END IF;

    cv := coalesce((item->>'can_view')::boolean,false);

    INSERT INTO public.app_permissions(
      user_id,module_key,can_view,can_create,can_edit,can_delete,can_export,updated_at
    ) VALUES (
      p_user_id,
      mk,
      cv,
      cv AND coalesce((item->>'can_create')::boolean,false),
      cv AND coalesce((item->>'can_edit')::boolean,false),
      cv AND coalesce((item->>'can_delete')::boolean,false),
      cv AND coalesce((item->>'can_export')::boolean,false),
      now()
    );
  END LOOP;
END;
$$;

REVOKE ALL ON FUNCTION public.admin_replace_user_permissions(uuid,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_replace_user_permissions(uuid,jsonb) TO authenticated;


-- Cambio de contraseña de otro usuario. Sustituye la versión anterior y añade
-- validaciones consistentes con el alta.
CREATE OR REPLACE FUNCTION public.admin_set_user_password(
  p_user_id uuid,
  p_new_password text
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth, extensions
AS $$
BEGIN
  IF NOT (public.is_admin() OR public.has_permission('usuarios','edit')) THEN
    RAISE EXCEPTION 'No autorizado';
  END IF;

  IF p_new_password IS NULL OR length(p_new_password) < 8 OR length(p_new_password) > 72 THEN
    RAISE EXCEPTION 'La contraseña debe tener entre 8 y 72 caracteres';
  END IF;

  UPDATE auth.users
  SET encrypted_password = crypt(p_new_password, gen_salt('bf')),
      email_confirmed_at = coalesce(email_confirmed_at, now()),
      updated_at = now()
  WHERE id = p_user_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Usuario no encontrado';
  END IF;
END;
$$;

REVOKE ALL ON FUNCTION public.admin_set_user_password(uuid,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_set_user_password(uuid,text) TO authenticated;

-- Permisos de Data API requeridos para los módulos administrativos.
GRANT SELECT, INSERT, UPDATE, DELETE ON public.app_profiles TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.app_permissions TO authenticated;

-- Verificación rápida al finalizar.
SELECT
  '04_USUARIOS_PERMISOS_ESTABLE instalado' AS estado,
  count(*) AS perfiles_actuales
FROM public.app_profiles;
