-- Enterprise business-role bridge.
-- Keeps legacy app_user.role intact during migration while separating business
-- hierarchy from System Admin permission.

CREATE TABLE IF NOT EXISTS public.ws_access_profile (
  user_id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  business_role text NOT NULL,
  system_admin boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_access_profile_user_fk FOREIGN KEY (tenant_id, user_id)
    REFERENCES public.app_user(tenant_id, id) ON DELETE CASCADE,
  CONSTRAINT ws_access_profile_role_ck CHECK (
    business_role IN (
      'executive','delivery_manager','recruiter','compliance','operations','read_only'
    )
  ),
  CONSTRAINT ws_access_profile_tenant_user_uq UNIQUE (tenant_id, user_id)
);

INSERT INTO public.ws_access_profile(
  user_id, tenant_id, business_role, system_admin, created_at, updated_at
)
SELECT
  u.id,
  u.tenant_id,
  CASE u.role
    WHEN 'admin' THEN 'executive'
    WHEN 'manager' THEN 'delivery_manager'
    WHEN 'recruiter' THEN 'recruiter'
    WHEN 'operations' THEN 'operations'
    ELSE 'read_only'
  END,
  CASE WHEN u.role='admin' THEN true ELSE false END,
  now(),
  now()
FROM public.app_user u
ON CONFLICT (user_id) DO NOTHING;


CREATE OR REPLACE FUNCTION workspace_admin.sync_access_profile_from_legacy_role()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $
BEGIN
  INSERT INTO public.ws_access_profile(
    user_id, tenant_id, business_role, system_admin, created_at, updated_at
  )
  VALUES (
    NEW.id,
    NEW.tenant_id,
    CASE NEW.role
      WHEN 'admin' THEN 'executive'
      WHEN 'manager' THEN 'delivery_manager'
      WHEN 'recruiter' THEN 'recruiter'
      WHEN 'operations' THEN 'operations'
      ELSE 'read_only'
    END,
    CASE WHEN NEW.role='admin' THEN true ELSE false END,
    now(),
    now()
  )
  ON CONFLICT (user_id)
  DO UPDATE SET
    tenant_id = EXCLUDED.tenant_id,
    business_role = CASE
      -- Preserve an explicitly separated business role once legacy admin
      -- is no longer the only authority source.
      WHEN public.ws_access_profile.business_role NOT IN (
        'executive','delivery_manager','recruiter','operations','read_only'
      ) THEN public.ws_access_profile.business_role
      ELSE EXCLUDED.business_role
    END,
    system_admin = CASE
      WHEN NEW.role='admin' THEN true
      ELSE public.ws_access_profile.system_admin
    END,
    updated_at = now();
  RETURN NEW;
END
$;

DROP TRIGGER IF EXISTS ws_sync_access_profile ON public.app_user;
CREATE TRIGGER ws_sync_access_profile
AFTER INSERT OR UPDATE OF role ON public.app_user
FOR EACH ROW EXECUTE FUNCTION workspace_admin.sync_access_profile_from_legacy_role();

CREATE INDEX IF NOT EXISTS idx_ws_access_profile_tenant_role
  ON public.ws_access_profile(tenant_id, business_role, system_admin);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='medlivo_team_api_runtime') THEN
    EXECUTE 'GRANT SELECT ON public.ws_access_profile TO medlivo_team_api_runtime';
  END IF;
END
$$;
