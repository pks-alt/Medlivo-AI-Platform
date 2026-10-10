-- Submission → Interview → Offer → Start projections and Medlivo-owned start readiness.
-- JobDiva remains source of record for funnel stages; Medlivo owns readiness/risk overlays.

CREATE TABLE IF NOT EXISTS public.ws_submission_projection (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  job_id uuid NOT NULL,
  candidate_id uuid NOT NULL,
  recruiter_user_id uuid,
  source_system text NOT NULL DEFAULT 'jobdiva',
  source_submission_id text NOT NULL,
  source_status text NOT NULL,
  submitted_at timestamptz,
  client_response_at timestamptz,
  source_updated_at timestamptz,
  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  synced_at timestamptz NOT NULL,
  CONSTRAINT ws_submission_projection_job_fk FOREIGN KEY (tenant_id, job_id)
    REFERENCES public.job(tenant_id, id),
  CONSTRAINT ws_submission_projection_candidate_fk FOREIGN KEY (tenant_id, candidate_id)
    REFERENCES public.candidate(tenant_id, id),
  CONSTRAINT ws_submission_projection_recruiter_fk FOREIGN KEY (tenant_id, recruiter_user_id)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_submission_projection_source_uq UNIQUE (tenant_id, source_system, source_submission_id)
);

CREATE TABLE IF NOT EXISTS public.ws_interview_projection (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  job_id uuid NOT NULL,
  candidate_id uuid NOT NULL,
  submission_projection_id uuid,
  source_system text NOT NULL DEFAULT 'jobdiva',
  source_interview_id text NOT NULL,
  source_status text NOT NULL,
  interview_type text,
  scheduled_at timestamptz,
  completed_at timestamptz,
  outcome text,
  outcome_at timestamptz,
  source_updated_at timestamptz,
  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  synced_at timestamptz NOT NULL,
  CONSTRAINT ws_interview_projection_job_fk FOREIGN KEY (tenant_id, job_id)
    REFERENCES public.job(tenant_id, id),
  CONSTRAINT ws_interview_projection_candidate_fk FOREIGN KEY (tenant_id, candidate_id)
    REFERENCES public.candidate(tenant_id, id),
  CONSTRAINT ws_interview_projection_submission_fk FOREIGN KEY (submission_projection_id)
    REFERENCES public.ws_submission_projection(id),
  CONSTRAINT ws_interview_projection_source_uq UNIQUE (tenant_id, source_system, source_interview_id)
);

CREATE TABLE IF NOT EXISTS public.ws_offer_projection (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  job_id uuid NOT NULL,
  candidate_id uuid NOT NULL,
  submission_projection_id uuid,
  source_system text NOT NULL DEFAULT 'jobdiva',
  source_offer_id text NOT NULL,
  source_status text NOT NULL,
  offered_at timestamptz,
  accepted_at timestamptz,
  declined_at timestamptz,
  decline_reason text,
  source_updated_at timestamptz,
  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  synced_at timestamptz NOT NULL,
  CONSTRAINT ws_offer_projection_job_fk FOREIGN KEY (tenant_id, job_id)
    REFERENCES public.job(tenant_id, id),
  CONSTRAINT ws_offer_projection_candidate_fk FOREIGN KEY (tenant_id, candidate_id)
    REFERENCES public.candidate(tenant_id, id),
  CONSTRAINT ws_offer_projection_submission_fk FOREIGN KEY (submission_projection_id)
    REFERENCES public.ws_submission_projection(id),
  CONSTRAINT ws_offer_projection_source_uq UNIQUE (tenant_id, source_system, source_offer_id)
);

CREATE TABLE IF NOT EXISTS public.ws_placement_projection (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  job_id uuid NOT NULL,
  candidate_id uuid NOT NULL,
  source_system text NOT NULL DEFAULT 'jobdiva',
  source_placement_id text NOT NULL,
  source_status text NOT NULL,
  placement_status text,
  planned_start_date date,
  actual_start_date date,
  planned_end_date date,
  actual_end_date date,
  source_updated_at timestamptz,
  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  synced_at timestamptz NOT NULL,
  CONSTRAINT ws_placement_projection_job_fk FOREIGN KEY (tenant_id, job_id)
    REFERENCES public.job(tenant_id, id),
  CONSTRAINT ws_placement_projection_candidate_fk FOREIGN KEY (tenant_id, candidate_id)
    REFERENCES public.candidate(tenant_id, id),
  CONSTRAINT ws_placement_projection_source_uq UNIQUE (tenant_id, source_system, source_placement_id)
);

CREATE TABLE IF NOT EXISTS public.ws_start_readiness (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  job_id uuid NOT NULL,
  candidate_id uuid NOT NULL,
  placement_projection_id uuid,
  status text NOT NULL DEFAULT 'not_started',
  risk_level text NOT NULL DEFAULT 'unknown',
  risk_reason text,
  next_action text,
  owner_user_id uuid,
  due_at timestamptz,
  version integer NOT NULL DEFAULT 1,
  updated_by uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_start_readiness_job_fk FOREIGN KEY (tenant_id, job_id)
    REFERENCES public.job(tenant_id, id),
  CONSTRAINT ws_start_readiness_candidate_fk FOREIGN KEY (tenant_id, candidate_id)
    REFERENCES public.candidate(tenant_id, id),
  CONSTRAINT ws_start_readiness_placement_fk FOREIGN KEY (placement_projection_id)
    REFERENCES public.ws_placement_projection(id),
  CONSTRAINT ws_start_readiness_owner_fk FOREIGN KEY (tenant_id, owner_user_id)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_start_readiness_updated_by_fk FOREIGN KEY (tenant_id, updated_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_start_readiness_pair_uq UNIQUE (tenant_id, job_id, candidate_id),
  CONSTRAINT ws_start_readiness_status_ck CHECK (
    status IN ('not_started','in_progress','ready','blocked','started')
  ),
  CONSTRAINT ws_start_readiness_risk_ck CHECK (
    risk_level IN ('unknown','low','medium','high','critical')
  ),
  CONSTRAINT ws_start_readiness_version_ck CHECK (version > 0)
);

CREATE TABLE IF NOT EXISTS public.ws_start_readiness_item (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  readiness_id uuid NOT NULL,
  item_key text NOT NULL,
  label text NOT NULL,
  category text NOT NULL,
  status text NOT NULL DEFAULT 'missing',
  required boolean NOT NULL DEFAULT true,
  source_type text,
  source_reference text,
  due_at timestamptz,
  notes text,
  updated_by uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_start_readiness_item_readiness_fk FOREIGN KEY (readiness_id)
    REFERENCES public.ws_start_readiness(id),
  CONSTRAINT ws_start_readiness_item_user_fk FOREIGN KEY (tenant_id, updated_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_start_readiness_item_status_ck CHECK (
    status IN ('missing','pending','complete','waived','not_applicable')
  ),
  CONSTRAINT ws_start_readiness_item_uq UNIQUE (readiness_id, item_key)
);

CREATE INDEX IF NOT EXISTS idx_ws_submission_projection_pair
  ON public.ws_submission_projection(tenant_id, job_id, candidate_id, submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_ws_interview_projection_pair
  ON public.ws_interview_projection(tenant_id, job_id, candidate_id, scheduled_at DESC);
CREATE INDEX IF NOT EXISTS idx_ws_offer_projection_pair
  ON public.ws_offer_projection(tenant_id, job_id, candidate_id, offered_at DESC);
CREATE INDEX IF NOT EXISTS idx_ws_placement_projection_start
  ON public.ws_placement_projection(tenant_id, planned_start_date, source_status);
CREATE INDEX IF NOT EXISTS idx_ws_start_readiness_risk
  ON public.ws_start_readiness(tenant_id, risk_level, status, due_at);
CREATE INDEX IF NOT EXISTS idx_ws_start_readiness_item_status
  ON public.ws_start_readiness_item(tenant_id, readiness_id, status, due_at);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='medlivo_team_api_runtime') THEN
    EXECUTE 'GRANT SELECT ON public.ws_submission_projection TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT ON public.ws_interview_projection TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT ON public.ws_offer_projection TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT ON public.ws_placement_projection TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_start_readiness TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_start_readiness_item TO medlivo_team_api_runtime';
  END IF;
END
$$;
