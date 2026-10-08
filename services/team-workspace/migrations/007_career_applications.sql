-- Public career applications tied to manager-approved jobs.
-- Apply after 006_job_publication_approval.sql.

CREATE TABLE IF NOT EXISTS public.career_application (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  publication_id uuid NOT NULL,
  candidate_id uuid,
  applicant_name text NOT NULL,
  email text NOT NULL,
  phone text,
  profession text,
  specialty text,
  preferred_location text,
  availability text,
  resume_url text,
  consent_to_contact boolean NOT NULL DEFAULT false,
  source text NOT NULL DEFAULT 'medlivo_website',
  status text NOT NULL DEFAULT 'new',
  ownership_status text NOT NULL DEFAULT 'pending_lookup',
  assigned_recruiter_user_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT career_application_tenant_fk FOREIGN KEY (tenant_id)
    REFERENCES public.tenant(id),
  CONSTRAINT career_application_publication_fk FOREIGN KEY (tenant_id, publication_id)
    REFERENCES public.ws_job_publication(tenant_id, id),
  CONSTRAINT career_application_candidate_fk FOREIGN KEY (tenant_id, candidate_id)
    REFERENCES public.candidate(tenant_id, id),
  CONSTRAINT career_application_recruiter_fk FOREIGN KEY (tenant_id, assigned_recruiter_user_id)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT career_application_status_ck CHECK (
    status IN ('new','matched_existing_candidate','needs_candidate_create','assigned','contacted','closed')
  ),
  CONSTRAINT career_application_ownership_ck CHECK (
    ownership_status IN ('pending_lookup','owned','unowned','conflict','assigned')
  )
);

CREATE INDEX IF NOT EXISTS idx_career_application_publication_created
  ON public.career_application(tenant_id, publication_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_career_application_email
  ON public.career_application(tenant_id, lower(email), created_at DESC);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='medlivo_team_api_runtime') THEN
    EXECUTE 'GRANT SELECT ON public.career_application TO medlivo_team_api_runtime';
  END IF;
END
$$;
