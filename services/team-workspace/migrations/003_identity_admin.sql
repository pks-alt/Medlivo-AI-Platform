-- Admin provisioning and secure first-login identity binding.
-- Apply as a migration administrator after 001_workspace.sql.
-- Runtime roles receive EXECUTE only; they do not receive INSERT/UPDATE on app_user,
-- recruiter_profile, team or ws_identity.

CREATE SCHEMA IF NOT EXISTS workspace_admin;
REVOKE ALL ON SCHEMA workspace_admin FROM PUBLIC;

CREATE OR REPLACE FUNCTION workspace_admin.bind_google_identity(
  p_provider text,
  p_subject text,
  p_email text
) RETURNS TABLE(bound boolean)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
  v_user_id uuid;
  v_tenant_id uuid;
  v_count integer;
BEGIN
  IF p_provider <> 'google'
     OR p_subject IS NULL OR length(p_subject) < 1 OR length(p_subject) > 255
     OR p_email IS NULL OR lower(p_email) !~ '^[^[:space:]@]+@medlivo[.]com$'
  THEN
    RETURN QUERY SELECT false;
    RETURN;
  END IF;

  -- Idempotent re-login is allowed only when this subject is already bound to
  -- the same active, supported Medlivo account.
  SELECT u.id, u.tenant_id
    INTO v_user_id, v_tenant_id
  FROM public.ws_identity i
  JOIN public.app_user u
    ON u.id = i.user_id AND u.tenant_id = i.tenant_id
  WHERE i.provider = p_provider
    AND i.subject = p_subject
    AND u.is_active = true
    AND u.role IN ('admin','manager','recruiter')
    AND lower(u.email) = lower(p_email);

  IF FOUND THEN
    RETURN QUERY SELECT true;
    RETURN;
  END IF;

  -- A Google subject already bound elsewhere can never be rebound implicitly.
  IF EXISTS (
    SELECT 1 FROM public.ws_identity
    WHERE provider = p_provider AND subject = p_subject
  ) THEN
    RETURN QUERY SELECT false;
    RETURN;
  END IF;

  -- Email is only a lookup after Google has cryptographically verified it.
  -- Ambiguous or already-bound accounts fail closed.
  SELECT count(*)::integer
    INTO v_count
  FROM public.app_user u
  WHERE lower(u.email) = lower(p_email)
    AND u.is_active = true
    AND u.role IN ('admin','manager','recruiter')
    AND NOT EXISTS (
      SELECT 1 FROM public.ws_identity i
      WHERE i.provider = p_provider
        AND i.tenant_id = u.tenant_id
        AND i.user_id = u.id
    );

  IF v_count <> 1 THEN
    RETURN QUERY SELECT false;
    RETURN;
  END IF;

  SELECT u.id, u.tenant_id
    INTO v_user_id, v_tenant_id
  FROM public.app_user u
  WHERE lower(u.email) = lower(p_email)
    AND u.is_active = true
    AND u.role IN ('admin','manager','recruiter')
    AND NOT EXISTS (
      SELECT 1 FROM public.ws_identity i
      WHERE i.provider = p_provider
        AND i.tenant_id = u.tenant_id
        AND i.user_id = u.id
    )
  LIMIT 1
  FOR UPDATE;

  INSERT INTO public.ws_identity(provider, subject, tenant_id, user_id)
  VALUES (p_provider, p_subject, v_tenant_id, v_user_id)
  ON CONFLICT DO NOTHING;

  RETURN QUERY SELECT EXISTS (
    SELECT 1 FROM public.ws_identity
    WHERE provider = p_provider
      AND subject = p_subject
      AND tenant_id = v_tenant_id
      AND user_id = v_user_id
  );
END
$$;

CREATE OR REPLACE FUNCTION workspace_admin.provision_user(
  p_actor_user_id uuid,
  p_email text,
  p_display_name text,
  p_role text,
  p_team_id uuid,
  p_is_active boolean
) RETURNS TABLE(
  user_id uuid,
  email text,
  display_name text,
  role text,
  is_active boolean,
  team_id uuid
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
  v_tenant_id uuid;
  v_user_id uuid;
BEGIN
  SELECT u.tenant_id INTO v_tenant_id
  FROM public.app_user u
  WHERE u.id = p_actor_user_id
    AND u.is_active = true
    AND u.role = 'admin';

  IF NOT FOUND THEN
    RETURN;
  END IF;

  p_email := lower(p_email);
  IF p_email !~ '^[^[:space:]@]+@medlivo[.]com$'
     OR p_display_name IS NULL OR length(trim(p_display_name)) < 1 OR length(p_display_name) > 200
     OR p_role NOT IN ('admin','manager','recruiter','operations')
  THEN
    RETURN;
  END IF;

  IF p_role IN ('manager','recruiter') AND p_team_id IS NULL THEN
    RETURN;
  END IF;

  IF p_team_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.team t
    WHERE t.id = p_team_id AND t.tenant_id = v_tenant_id
  ) THEN
    RETURN;
  END IF;

  INSERT INTO public.app_user(tenant_id,email,display_name,role,is_active)
  VALUES (v_tenant_id,p_email,trim(p_display_name),p_role,p_is_active)
  ON CONFLICT (tenant_id,email)
  DO UPDATE SET display_name = EXCLUDED.display_name,
                role = EXCLUDED.role,
                is_active = EXCLUDED.is_active,
                updated_at = now()
  RETURNING id INTO v_user_id;

  IF p_role IN ('manager','recruiter') THEN
    INSERT INTO public.recruiter_profile(user_id,tenant_id,team_id)
    VALUES (v_user_id,v_tenant_id,p_team_id)
    ON CONFLICT (user_id)
    DO UPDATE SET tenant_id = EXCLUDED.tenant_id,
                  team_id = EXCLUDED.team_id,
                  updated_at = now();
  ELSE
    DELETE FROM public.recruiter_profile
    WHERE user_id = v_user_id AND tenant_id = v_tenant_id;
  END IF;

  IF p_role = 'manager' THEN
    UPDATE public.team
    SET manager_user_id = v_user_id
    WHERE id = p_team_id AND tenant_id = v_tenant_id;
  END IF;

  RETURN QUERY
  SELECT u.id,u.email,u.display_name,u.role,u.is_active,rp.team_id
  FROM public.app_user u
  LEFT JOIN public.recruiter_profile rp
    ON rp.user_id = u.id AND rp.tenant_id = u.tenant_id
  WHERE u.id = v_user_id AND u.tenant_id = v_tenant_id;
END
$$;

REVOKE ALL ON FUNCTION workspace_admin.bind_google_identity(text,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION workspace_admin.provision_user(uuid,text,text,text,uuid,boolean) FROM PUBLIC;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'medlivo_team_api_runtime') THEN
    EXECUTE 'GRANT USAGE ON SCHEMA workspace_admin TO medlivo_team_api_runtime';
    EXECUTE 'GRANT EXECUTE ON FUNCTION workspace_admin.bind_google_identity(text,text,text) TO medlivo_team_api_runtime';
    EXECUTE 'GRANT EXECUTE ON FUNCTION workspace_admin.provision_user(uuid,text,text,text,uuid,boolean) TO medlivo_team_api_runtime';
  END IF;
END
$$;
