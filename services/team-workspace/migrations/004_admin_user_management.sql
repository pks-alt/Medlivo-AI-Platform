-- Audited administrator user-management changes.
-- Apply after 003_identity_admin.sql.
-- Runtime can read audit history and execute guarded SECURITY DEFINER functions,
-- but still receives no direct UPDATE/INSERT privileges on canonical user tables.

CREATE TABLE IF NOT EXISTS public.ws_admin_audit (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  actor_user_id uuid NOT NULL,
  target_user_id uuid NOT NULL,
  action text NOT NULL,
  before_state jsonb NOT NULL,
  after_state jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_admin_audit_actor_fk FOREIGN KEY (tenant_id, actor_user_id)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_admin_audit_target_fk FOREIGN KEY (tenant_id, target_user_id)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_admin_audit_action CHECK (action IN ('user.provisioned','user.updated'))
);

CREATE INDEX IF NOT EXISTS idx_ws_admin_audit_tenant_created
  ON public.ws_admin_audit(tenant_id, created_at DESC, id);

DROP TRIGGER IF EXISTS ws_admin_audit_append_only ON public.ws_admin_audit;
CREATE TRIGGER ws_admin_audit_append_only
BEFORE UPDATE OR DELETE ON public.ws_admin_audit
FOR EACH ROW EXECUTE FUNCTION public.ws_reject_audit_mutation();

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
  v_before jsonb := '{}'::jsonb;
  v_after jsonb;
BEGIN
  SELECT u.tenant_id INTO v_tenant_id
  FROM public.app_user u
  WHERE u.id = p_actor_user_id AND u.is_active = true AND u.role = 'admin';

  IF NOT FOUND THEN RETURN; END IF;

  p_email := lower(p_email);
  IF p_email !~ '^[^[:space:]@]+@medlivo[.]com$'
     OR p_display_name IS NULL OR length(trim(p_display_name)) < 1 OR length(p_display_name) > 200
     OR p_role NOT IN ('admin','manager','recruiter','operations')
  THEN RETURN; END IF;

  IF p_role IN ('manager','recruiter') AND p_team_id IS NULL THEN RETURN; END IF;
  IF p_team_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.team t WHERE t.id = p_team_id AND t.tenant_id = v_tenant_id
  ) THEN RETURN; END IF;

  SELECT jsonb_build_object(
      'email',u.email,'display_name',u.display_name,'role',u.role,'is_active',u.is_active,
      'team_id',rp.team_id)
    INTO v_before
  FROM public.app_user u
  LEFT JOIN public.recruiter_profile rp
    ON rp.user_id=u.id AND rp.tenant_id=u.tenant_id
  WHERE u.tenant_id=v_tenant_id AND lower(u.email)=p_email;

  SELECT u.id INTO v_user_id
  FROM public.app_user u
  WHERE u.tenant_id=v_tenant_id AND lower(u.email)=p_email
  FOR UPDATE;

  IF FOUND THEN
    UPDATE public.app_user u
    SET display_name=trim(p_display_name),role=p_role,is_active=p_is_active
    WHERE u.id=v_user_id AND u.tenant_id=v_tenant_id;
  ELSE
    INSERT INTO public.app_user(tenant_id,email,display_name,role,is_active)
    VALUES (v_tenant_id,p_email,trim(p_display_name),p_role,p_is_active)
    RETURNING app_user.id INTO v_user_id;
  END IF;

  UPDATE public.team SET manager_user_id=NULL
  WHERE tenant_id=v_tenant_id AND manager_user_id=v_user_id
    AND (p_role <> 'manager' OR id IS DISTINCT FROM p_team_id);

  IF p_role IN ('manager','recruiter') THEN
    INSERT INTO public.recruiter_profile(user_id,tenant_id,team_id)
    VALUES (v_user_id,v_tenant_id,p_team_id)
    ON CONFLICT (user_id)
    DO UPDATE SET tenant_id=EXCLUDED.tenant_id, team_id=EXCLUDED.team_id;
  ELSE
    DELETE FROM public.recruiter_profile
    WHERE user_id=v_user_id AND tenant_id=v_tenant_id;
  END IF;

  IF p_role='manager' THEN
    UPDATE public.team SET manager_user_id=v_user_id
    WHERE id=p_team_id AND tenant_id=v_tenant_id;
  END IF;

  SELECT jsonb_build_object(
      'email',u.email,'display_name',u.display_name,'role',u.role,'is_active',u.is_active,
      'team_id',rp.team_id)
    INTO v_after
  FROM public.app_user u
  LEFT JOIN public.recruiter_profile rp
    ON rp.user_id=u.id AND rp.tenant_id=u.tenant_id
  WHERE u.id=v_user_id AND u.tenant_id=v_tenant_id;

  INSERT INTO public.ws_admin_audit(id,tenant_id,actor_user_id,target_user_id,action,before_state,after_state)
  VALUES (gen_random_uuid(),v_tenant_id,p_actor_user_id,v_user_id,'user.provisioned',
          COALESCE(v_before,'{}'::jsonb),COALESCE(v_after,'{}'::jsonb));

  RETURN QUERY
  SELECT u.id,u.email,u.display_name,u.role,u.is_active,rp.team_id
  FROM public.app_user u
  LEFT JOIN public.recruiter_profile rp
    ON rp.user_id=u.id AND rp.tenant_id=u.tenant_id
  WHERE u.id=v_user_id AND u.tenant_id=v_tenant_id;
END
$$;

CREATE OR REPLACE FUNCTION workspace_admin.update_user(
  p_actor_user_id uuid,
  p_target_user_id uuid,
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
  v_before jsonb;
  v_after jsonb;
  v_old_role text;
  v_admin_count integer;
BEGIN
  SELECT u.tenant_id INTO v_tenant_id
  FROM public.app_user u
  WHERE u.id=p_actor_user_id AND u.is_active=true AND u.role='admin';
  IF NOT FOUND THEN RETURN; END IF;

  -- Self-service access changes are intentionally prohibited to prevent lockout.
  IF p_target_user_id=p_actor_user_id THEN RETURN; END IF;

  SELECT u.role,
         jsonb_build_object(
           'email',u.email,'display_name',u.display_name,'role',u.role,'is_active',u.is_active,
           'team_id',rp.team_id)
    INTO v_old_role,v_before
  FROM public.app_user u
  LEFT JOIN public.recruiter_profile rp
    ON rp.user_id=u.id AND rp.tenant_id=u.tenant_id
  WHERE u.id=p_target_user_id AND u.tenant_id=v_tenant_id
  FOR UPDATE OF u;
  IF NOT FOUND THEN RETURN; END IF;

  IF p_display_name IS NULL OR length(trim(p_display_name)) < 1 OR length(p_display_name) > 200
     OR p_role NOT IN ('admin','manager','recruiter','operations')
  THEN RETURN; END IF;

  IF p_role IN ('manager','recruiter') AND p_team_id IS NULL THEN RETURN; END IF;
  IF p_team_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.team t WHERE t.id=p_team_id AND t.tenant_id=v_tenant_id
  ) THEN RETURN; END IF;

  IF v_old_role='admin' AND (p_role<>'admin' OR p_is_active=false) THEN
    SELECT count(*)::integer INTO v_admin_count
    FROM public.app_user u
    WHERE u.tenant_id=v_tenant_id AND u.role='admin' AND u.is_active=true;
    IF v_admin_count <= 1 THEN RETURN; END IF;
  END IF;

  UPDATE public.app_user
  SET display_name=trim(p_display_name),role=p_role,is_active=p_is_active
  WHERE id=p_target_user_id AND tenant_id=v_tenant_id;

  UPDATE public.team SET manager_user_id=NULL
  WHERE tenant_id=v_tenant_id AND manager_user_id=p_target_user_id
    AND (p_role<>'manager' OR id IS DISTINCT FROM p_team_id);

  IF p_role IN ('manager','recruiter') THEN
    INSERT INTO public.recruiter_profile(user_id,tenant_id,team_id)
    VALUES (p_target_user_id,v_tenant_id,p_team_id)
    ON CONFLICT (user_id)
    DO UPDATE SET tenant_id=EXCLUDED.tenant_id,team_id=EXCLUDED.team_id;
  ELSE
    DELETE FROM public.recruiter_profile
    WHERE user_id=p_target_user_id AND tenant_id=v_tenant_id;
  END IF;

  IF p_role='manager' THEN
    UPDATE public.team SET manager_user_id=p_target_user_id
    WHERE id=p_team_id AND tenant_id=v_tenant_id;
  END IF;

  SELECT jsonb_build_object(
      'email',u.email,'display_name',u.display_name,'role',u.role,'is_active',u.is_active,
      'team_id',rp.team_id)
    INTO v_after
  FROM public.app_user u
  LEFT JOIN public.recruiter_profile rp
    ON rp.user_id=u.id AND rp.tenant_id=u.tenant_id
  WHERE u.id=p_target_user_id AND u.tenant_id=v_tenant_id;

  INSERT INTO public.ws_admin_audit(id,tenant_id,actor_user_id,target_user_id,action,before_state,after_state)
  VALUES (gen_random_uuid(),v_tenant_id,p_actor_user_id,p_target_user_id,'user.updated',
          COALESCE(v_before,'{}'::jsonb),COALESCE(v_after,'{}'::jsonb));

  RETURN QUERY
  SELECT u.id,u.email,u.display_name,u.role,u.is_active,rp.team_id
  FROM public.app_user u
  LEFT JOIN public.recruiter_profile rp
    ON rp.user_id=u.id AND rp.tenant_id=u.tenant_id
  WHERE u.id=p_target_user_id AND u.tenant_id=v_tenant_id;
END
$$;

REVOKE ALL ON public.ws_admin_audit FROM PUBLIC;
REVOKE ALL ON FUNCTION workspace_admin.update_user(uuid,uuid,text,text,uuid,boolean) FROM PUBLIC;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='medlivo_team_api_runtime') THEN
    EXECUTE 'GRANT SELECT ON public.ws_admin_audit TO medlivo_team_api_runtime';
    EXECUTE 'GRANT EXECUTE ON FUNCTION workspace_admin.update_user(uuid,uuid,text,text,uuid,boolean) TO medlivo_team_api_runtime';
  END IF;
END
$$;
