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

CREATE INDEX IF NOT EXISTS idx_ws_access_profile_tenant_role
  ON public.ws_access_profile(tenant_id, business_role, system_admin);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='medlivo_team_api_runtime') THEN
    EXECUTE 'GRANT SELECT ON public.ws_access_profile TO medlivo_team_api_runtime';
  END IF;
END
$$;
