-- Versioned Medlivo Job Content Standards used by all job sources and renderers.
CREATE TABLE IF NOT EXISTS public.ws_job_content_standard (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  division text NOT NULL,
  profession text NOT NULL,
  specialty text,
  care_setting text,
  display_title text NOT NULL,
  version integer NOT NULL,
  status text NOT NULL,
  content jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by uuid NOT NULL,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL,
  CONSTRAINT ws_job_content_standard_tenant_fk FOREIGN KEY (tenant_id) REFERENCES public.tenant(id),
  CONSTRAINT ws_job_content_standard_creator_fk FOREIGN KEY (tenant_id, created_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_job_content_standard_division_ck CHECK (
    division IN ('Rehabilitation','Nursing & Allied','Locum Tenens')
  ),
  CONSTRAINT ws_job_content_standard_status_ck CHECK (
    status IN ('draft','active','retired')
  ),
  CONSTRAINT ws_job_content_standard_version_ck CHECK (version > 0),
  CONSTRAINT ws_job_content_standard_identity_uq UNIQUE (
    tenant_id, division, profession, specialty, care_setting, version
  )
);

CREATE INDEX IF NOT EXISTS idx_ws_job_content_standard_lookup
  ON public.ws_job_content_standard
  (tenant_id, division, profession, specialty, care_setting, status, version DESC);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='medlivo_team_api_runtime') THEN
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_job_content_standard TO medlivo_team_api_runtime';
  END IF;
END
$$;
