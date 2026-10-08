-- Phase 1 manager approval for Medlivo-enhanced jobs.
-- Apply after 005_phase1_operations.sql.

CREATE TABLE IF NOT EXISTS public.ws_job_publication (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  team_id uuid,
  job_id uuid,
  intake_item_id uuid,
  source_snapshot jsonb NOT NULL,
  enhanced_snapshot jsonb NOT NULL,
  quality_score jsonb NOT NULL DEFAULT '{}'::jsonb,
  readiness text NOT NULL DEFAULT 'manager_review',
  recruiting_status text NOT NULL DEFAULT 'pending',
  website_status text NOT NULL DEFAULT 'pending',
  recruiting_approved_by uuid,
  recruiting_approved_at timestamptz,
  website_approved_by uuid,
  website_approved_at timestamptz,
  version integer NOT NULL DEFAULT 1,
  created_by uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_job_publication_tenant_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT ws_job_publication_team_fk FOREIGN KEY (tenant_id, team_id)
    REFERENCES public.team(tenant_id, id),
  CONSTRAINT ws_job_publication_job_fk FOREIGN KEY (tenant_id, job_id)
    REFERENCES public.job(tenant_id, id),
  CONSTRAINT ws_job_publication_item_fk FOREIGN KEY (tenant_id, intake_item_id)
    REFERENCES public.ws_job_intake_item(tenant_id, id),
  CONSTRAINT ws_job_publication_created_by_fk FOREIGN KEY (tenant_id, created_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_job_publication_recruiting_by_fk FOREIGN KEY (tenant_id, recruiting_approved_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_job_publication_website_by_fk FOREIGN KEY (tenant_id, website_approved_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_job_publication_readiness_ck CHECK (
    readiness IN ('not_ready','manager_review','ready_for_recruiting','ready_to_publish')
  ),
  CONSTRAINT ws_job_publication_recruiting_ck CHECK (
    recruiting_status IN ('pending','approved','rejected')
  ),
  CONSTRAINT ws_job_publication_website_ck CHECK (
    website_status IN ('pending','approved','rejected')
  ),
  CONSTRAINT ws_job_publication_version_ck CHECK (version > 0),
  CONSTRAINT ws_job_publication_one_source_ck CHECK (
    (job_id IS NOT NULL AND intake_item_id IS NULL) OR
    (job_id IS NULL AND intake_item_id IS NOT NULL)
  )
);

CREATE INDEX IF NOT EXISTS idx_ws_job_publication_team_status
  ON public.ws_job_publication(tenant_id, team_id, recruiting_status, website_status, updated_at DESC);

CREATE TABLE IF NOT EXISTS public.ws_job_publication_audit (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  publication_id uuid NOT NULL,
  actor_user_id uuid NOT NULL,
  action text NOT NULL,
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_job_publication_audit_publication_fk FOREIGN KEY (tenant_id, publication_id)
    REFERENCES public.ws_job_publication(tenant_id, id) ON DELETE CASCADE,
  CONSTRAINT ws_job_publication_audit_actor_fk FOREIGN KEY (tenant_id, actor_user_id)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_job_publication_audit_action_ck CHECK (
    action IN ('draft.created','recruiting.approved','recruiting.rejected','website.approved','website.rejected','draft.updated')
  )
);

CREATE INDEX IF NOT EXISTS idx_ws_job_publication_audit_pub_created
  ON public.ws_job_publication_audit(tenant_id, publication_id, created_at DESC, id);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='medlivo_team_api_runtime') THEN
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_job_publication TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT ON public.ws_job_publication_audit TO medlivo_team_api_runtime';
  END IF;
END
$$;
