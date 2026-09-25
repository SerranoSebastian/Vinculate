-- Vincúlate SEDECO - complemento final para perfiles/permisos delegables
-- Ejecutar UNA VEZ en SQL Editor del mismo proyecto Supabase.

-- 1) Delegación real para perfiles
DROP POLICY IF EXISTS profiles_admin_insert ON public.app_profiles;
CREATE POLICY profiles_admin_insert ON public.app_profiles
FOR INSERT TO authenticated
WITH CHECK (public.is_admin() OR public.has_permission('usuarios','create'));

DROP POLICY IF EXISTS profiles_admin_update ON public.app_profiles;
CREATE POLICY profiles_admin_update ON public.app_profiles
FOR UPDATE TO authenticated
USING (public.is_admin() OR public.has_permission('usuarios','edit'))
WITH CHECK (public.is_admin() OR public.has_permission('usuarios','edit'));

DROP POLICY IF EXISTS profiles_self_or_admin_select ON public.app_profiles;
CREATE POLICY profiles_self_or_admin_select ON public.app_profiles
FOR SELECT TO authenticated
USING (
  user_id = auth.uid()
  OR public.is_admin()
  OR public.has_permission('usuarios','view')
);

-- 2) Delegación real para matriz de permisos
DROP POLICY IF EXISTS permissions_self_or_admin_select ON public.app_permissions;
CREATE POLICY permissions_self_or_admin_select ON public.app_permissions
FOR SELECT TO authenticated
USING (
  user_id = auth.uid()
  OR public.is_admin()
  OR public.has_permission('usuarios','view')
);

DROP POLICY IF EXISTS permissions_admin_insert ON public.app_permissions;
CREATE POLICY permissions_admin_insert ON public.app_permissions
FOR INSERT TO authenticated
WITH CHECK (public.is_admin() OR public.has_permission('usuarios','edit'));

DROP POLICY IF EXISTS permissions_admin_update ON public.app_permissions;
CREATE POLICY permissions_admin_update ON public.app_permissions
FOR UPDATE TO authenticated
USING (public.is_admin() OR public.has_permission('usuarios','edit'))
WITH CHECK (public.is_admin() OR public.has_permission('usuarios','edit'));

DROP POLICY IF EXISTS permissions_admin_delete ON public.app_permissions;
CREATE POLICY permissions_admin_delete ON public.app_permissions
FOR DELETE TO authenticated
USING (public.is_admin() OR public.has_permission('usuarios','delete'));

-- 3) Delegación de administración de equipos
DROP POLICY IF EXISTS devices_self_or_admin_select ON public.app_devices;
CREATE POLICY devices_self_or_admin_select ON public.app_devices
FOR SELECT TO authenticated
USING (
  user_id = auth.uid()
  OR public.is_admin()
  OR public.has_permission('dispositivos','view')
);

DROP POLICY IF EXISTS devices_self_or_admin_update ON public.app_devices;
CREATE POLICY devices_self_or_admin_update ON public.app_devices
FOR UPDATE TO authenticated
USING (
  ((user_id = auth.uid()) AND authorized = true AND public.is_active_user())
  OR public.is_admin()
  OR public.has_permission('dispositivos','edit')
)
WITH CHECK (
  ((user_id = auth.uid()) AND authorized = true AND public.is_active_user())
  OR public.is_admin()
  OR public.has_permission('dispositivos','edit')
);

DROP POLICY IF EXISTS devices_admin_delete ON public.app_devices;
CREATE POLICY devices_admin_delete ON public.app_devices
FOR DELETE TO authenticated
USING (public.is_admin() OR public.has_permission('dispositivos','delete'));

-- 4) Auditoría delegable
DROP POLICY IF EXISTS audit_admin_select ON public.app_audit_log;
CREATE POLICY audit_admin_select ON public.app_audit_log
FOR SELECT TO authenticated
USING (public.is_admin() OR public.has_permission('auditoria','view'));

-- 5) Cambio de contraseña de otro usuario desde la app.
-- La función vive en la BD; la app NO recibe service_role ni secret key.
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;

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

  IF p_new_password IS NULL OR length(p_new_password) < 8 THEN
    RAISE EXCEPTION 'La contraseña debe tener al menos 8 caracteres';
  END IF;

  UPDATE auth.users
  SET encrypted_password = extensions.crypt(p_new_password, extensions.gen_salt('bf')),
      updated_at = now()
  WHERE id = p_user_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Usuario no encontrado';
  END IF;
END;
$$;

REVOKE ALL ON FUNCTION public.admin_set_user_password(uuid,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.admin_set_user_password(uuid,text) TO authenticated;

-- 6) Asegurar acceso de usuarios autenticados a las tablas de control.
GRANT SELECT, INSERT, UPDATE, DELETE ON public.app_profiles TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.app_permissions TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.app_devices TO authenticated;
GRANT SELECT, INSERT ON public.app_audit_log TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.app_priorities TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.app_priority_notifications TO authenticated;

-- 7) Secuencias identity usadas desde Data API
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;
