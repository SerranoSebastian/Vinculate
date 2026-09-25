-- VINCÚLATE SEDECO — colocaciones + administración estable de cuentas
-- Fecha: 2026-09-18
-- Ejecutar UNA VEZ después de 04_USUARIOS_PERMISOS_ESTABLE.sql.
-- No elimina personas, vacantes ni vinculaciones existentes.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1. Colocaciones: se conserva la misma vinculación y se añade su resultado.
ALTER TABLE public.vinculaciones
  ADD COLUMN IF NOT EXISTS fecha_colocacion date;

UPDATE public.vinculaciones
SET estatus = 'Colocado'
WHERE lower(trim(coalesce(estatus,''))) IN ('contratado','colocado');

ALTER TABLE public.vinculaciones DROP CONSTRAINT IF EXISTS vinculaciones_estatus_check;
ALTER TABLE public.vinculaciones
  ADD CONSTRAINT vinculaciones_estatus_check
  CHECK (estatus IS NULL OR estatus IN ('Vinculado','Colocado','No vinculado'));

CREATE INDEX IF NOT EXISTS idx_vinc_estatus ON public.vinculaciones(estatus);
CREATE INDEX IF NOT EXISTS idx_vinc_fecha_colocacion ON public.vinculaciones(fecha_colocacion);

-- 2. Evitar dos perfiles con el mismo correo, incluso con mayúsculas distintas.
CREATE UNIQUE INDEX IF NOT EXISTS app_profiles_email_lower_uidx
ON public.app_profiles(lower(email));

-- 3. Actualiza correo, nombre, rol y estado en Auth + perfil de la app.
CREATE OR REPLACE FUNCTION public.admin_update_user_account(
  p_user_id uuid,
  p_email text,
  p_display_name text,
  p_role text,
  p_status text
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth, extensions
AS $$
DECLARE
  v_email text := lower(trim(coalesce(p_email,'')));
  v_name text := trim(coalesce(p_display_name,''));
BEGIN
  IF NOT (public.is_admin() OR public.has_permission('usuarios','edit')) THEN
    RAISE EXCEPTION 'No autorizado para modificar cuentas';
  END IF;
  IF v_email = '' OR v_email !~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$' THEN
    RAISE EXCEPTION 'Correo electrónico inválido';
  END IF;
  IF p_role NOT IN ('admin','collaborator') THEN RAISE EXCEPTION 'Rol inválido'; END IF;
  IF p_status NOT IN ('pending','active','disabled') THEN RAISE EXCEPTION 'Estado inválido'; END IF;
  IF v_name = '' THEN v_name := v_email; END IF;

  IF EXISTS (SELECT 1 FROM auth.users WHERE lower(email)=v_email AND id<>p_user_id) OR
     EXISTS (SELECT 1 FROM public.app_profiles WHERE lower(email)=v_email AND user_id<>p_user_id) THEN
    RAISE EXCEPTION 'Ese correo ya pertenece a otra cuenta';
  END IF;

  -- No permitir quitar el último administrador activo.
  IF EXISTS (SELECT 1 FROM public.app_profiles WHERE user_id=p_user_id AND role='admin' AND status='active')
     AND (p_role <> 'admin' OR p_status <> 'active')
     AND (SELECT count(*) FROM public.app_profiles WHERE role='admin' AND status='active') <= 1 THEN
    RAISE EXCEPTION 'No se puede desactivar o degradar al último administrador activo';
  END IF;

  UPDATE auth.users
  SET email=v_email,
      email_confirmed_at=coalesce(email_confirmed_at, now()),
      raw_user_meta_data=coalesce(raw_user_meta_data,'{}'::jsonb) || jsonb_build_object('display_name',v_name),
      updated_at=now()
  WHERE id=p_user_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'Usuario no encontrado en Authentication'; END IF;

  -- Mantener sincronizada la identidad email cuando exista.
  UPDATE auth.identities
  SET identity_data = coalesce(identity_data,'{}'::jsonb) || jsonb_build_object('email',v_email),
      updated_at = now()
  WHERE user_id=p_user_id AND provider='email';

  UPDATE public.app_profiles
  SET email=v_email, display_name=v_name, role=p_role, status=p_status
  WHERE user_id=p_user_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'Perfil Vincúlate no encontrado'; END IF;

  -- Bloquear equipos al deshabilitar la cuenta.
  IF p_status='disabled' THEN
    UPDATE public.app_devices SET authorized=false WHERE user_id=p_user_id;
  END IF;
END;
$$;
REVOKE ALL ON FUNCTION public.admin_update_user_account(uuid,text,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_update_user_account(uuid,text,text,text,text) TO authenticated;

-- 4. Baja definitiva. Protege la sesión actual y al último administrador.
CREATE OR REPLACE FUNCTION public.admin_delete_user_account(p_user_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth
AS $$
BEGIN
  IF NOT (public.is_admin() OR public.has_permission('usuarios','delete')) THEN
    RAISE EXCEPTION 'No autorizado para eliminar cuentas';
  END IF;
  IF p_user_id = auth.uid() THEN
    RAISE EXCEPTION 'No puedes eliminar tu propia cuenta durante una sesión activa';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM public.app_profiles WHERE user_id=p_user_id) THEN
    RAISE EXCEPTION 'Perfil no encontrado';
  END IF;
  IF EXISTS (SELECT 1 FROM public.app_profiles WHERE user_id=p_user_id AND role='admin' AND status='active')
     AND (SELECT count(*) FROM public.app_profiles WHERE role='admin' AND status='active') <= 1 THEN
    RAISE EXCEPTION 'No se puede eliminar al último administrador activo';
  END IF;

  -- Datos administrativos asociados a la cuenta. Los datos operativos se conservan.
  IF to_regclass('public.app_priority_notifications') IS NOT NULL THEN
    DELETE FROM public.app_priority_notifications WHERE user_id=p_user_id;
  END IF;
  IF to_regclass('public.app_priorities') IS NOT NULL THEN
    DELETE FROM public.app_priorities WHERE created_by=p_user_id;
  END IF;
  IF to_regclass('public.app_audit_log') IS NOT NULL THEN
    DELETE FROM public.app_audit_log WHERE user_id=p_user_id;
  END IF;
  DELETE FROM public.app_permissions WHERE user_id=p_user_id;
  DELETE FROM public.app_devices WHERE user_id=p_user_id;
  DELETE FROM public.app_profiles WHERE user_id=p_user_id;
  DELETE FROM auth.users WHERE id=p_user_id;
END;
$$;
REVOKE ALL ON FUNCTION public.admin_delete_user_account(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_delete_user_account(uuid) TO authenticated;

-- 5. Contraseña administrativa consistente con el alta.
CREATE OR REPLACE FUNCTION public.admin_set_user_password(p_user_id uuid, p_new_password text)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth, extensions
AS $$
BEGIN
  IF NOT (public.is_admin() OR public.has_permission('usuarios','edit')) THEN RAISE EXCEPTION 'No autorizado'; END IF;
  IF p_new_password IS NULL OR length(p_new_password)<8 OR length(p_new_password)>72 THEN
    RAISE EXCEPTION 'La contraseña debe tener entre 8 y 72 caracteres';
  END IF;
  UPDATE auth.users
  SET encrypted_password=extensions.crypt(p_new_password, extensions.gen_salt('bf')), updated_at=now()
  WHERE id=p_user_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'Usuario no encontrado'; END IF;
END;
$$;
REVOKE ALL ON FUNCTION public.admin_set_user_password(uuid,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_set_user_password(uuid,text) TO authenticated;

SELECT '05_COLOCACIONES_Y_CUENTAS_20260918 instalado' AS estado;
