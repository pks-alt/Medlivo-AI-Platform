-- Final Block 1 recruiter execution controls:
-- protected first-action window + candidate relationship continuity + meaningful engagement audit.

CREATE TABLE IF NOT EXISTS public.ws_business_calendar_exception (
  tenant_id uuid NOT NULL,
  calendar_date date NOT NULL,
  exception_type text NOT NULL,
  label text,
  created_at timestamptz NOT NULL,
  PRIMARY KEY (tenant_id, calendar_date),
  CONSTRAINT ws_business_calendar_exception_tenant_fk
    FOREIGN KEY (tenant_id) REFERENCES public.tenant(id),
  CONSTRAINT ws_business_calendar_exception_type_ck
    CHECK (exception_type IN ('holiday','working_day_override'))
);

CREATE TABLE IF NOT EXISTS public.ws_protected_action_window (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  job_id uuid NOT NULL,
  recruiter_user_id uuid NOT NULL,
  assignment_version integer,
  status text NOT NULL,
  assigned_at timestamptz NOT NULL,
  protected_until timestamptz NOT NULL,
  meaningful_action_at timestamptz,
  meaningful_action_type text,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL,
  CONSTRAINT ws_protected_action_window_job_fk
    FOREIGN KEY (tenant_id, job_id) REFERENCES public.job(tenant_id, id),
  CONSTRAINT ws_protected_action_window_recruiter_fk
    FOREIGN KEY (tenant_id, recruiter_user_id) REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_protected_action_window_status_ck
    CHECK (status IN ('protected','working','available_for_support','completed')),
  CONSTRAINT ws_protected_action_window_action_ck
    CHECK (
      meaningful_action_type IS NULL OR meaningful_action_type IN (
        'working','email_sent','sms_sent','call_completed',
        'follow_up_completed','next_step_recorded','submission_advanced',
        'interview_advanced','candidate_reply'
      )
    )
);

CREATE INDEX IF NOT EXISTS idx_ws_protected_action_recruiter
  ON public.ws_protected_action_window
  (tenant_id, recruiter_user_id, status, protected_until);

CREATE INDEX IF NOT EXISTS idx_ws_protected_action_job
  ON public.ws_protected_action_window
  (tenant_id, job_id, assigned_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_ws_protected_action_current_assignment
  ON public.ws_protected_action_window (tenant_id, job_id, recruiter_user_id, assignment_version)
  WHERE assignment_version IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.ws_candidate_relationship (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  candidate_id uuid NOT NULL,
  recruiter_user_id uuid NOT NULL,
  status text NOT NULL,
  started_at timestamptz NOT NULL,
  last_meaningful_at timestamptz NOT NULL,
  last_meaningful_type text NOT NULL,
  ended_at timestamptz,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL,
  CONSTRAINT ws_candidate_relationship_candidate_fk
    FOREIGN KEY (tenant_id, candidate_id) REFERENCES public.candidate(tenant_id, id),
  CONSTRAINT ws_candidate_relationship_recruiter_fk
    FOREIGN KEY (tenant_id, recruiter_user_id) REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_candidate_relationship_status_ck
    CHECK (status IN ('active','ended'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_ws_candidate_relationship_active
  ON public.ws_candidate_relationship (tenant_id, candidate_id)
  WHERE status='active';

CREATE INDEX IF NOT EXISTS idx_ws_candidate_relationship_recruiter
  ON public.ws_candidate_relationship
  (tenant_id, recruiter_user_id, status, last_meaningful_at DESC);

CREATE TABLE IF NOT EXISTS public.ws_candidate_engagement_event (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  candidate_id uuid NOT NULL,
  recruiter_user_id uuid NOT NULL,
  job_id uuid,
  event_type text NOT NULL,
  meaningful boolean NOT NULL,
  source_type text NOT NULL,
  source_reference text,
  occurred_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL,
  CONSTRAINT ws_candidate_engagement_candidate_fk
    FOREIGN KEY (tenant_id, candidate_id) REFERENCES public.candidate(tenant_id, id),
  CONSTRAINT ws_candidate_engagement_recruiter_fk
    FOREIGN KEY (tenant_id, recruiter_user_id) REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_candidate_engagement_job_fk
    FOREIGN KEY (tenant_id, job_id) REFERENCES public.job(tenant_id, id),
  CONSTRAINT ws_candidate_engagement_event_type_ck
    CHECK (event_type IN (
      'candidate_reply','completed_call','availability_confirmed',
      'preferences_confirmed','interest_confirmed','next_step_agreed',
      'email_sent','sms_sent','working','follow_up_completed',
      'submission_advanced','interview_advanced','profile_view','internal_note'
    )),
  CONSTRAINT ws_candidate_engagement_source_type_ck
    CHECK (source_type IN ('medlivo','gmail','zoom_phone','jobdiva','manual','system'))
);

CREATE INDEX IF NOT EXISTS idx_ws_candidate_engagement_candidate
  ON public.ws_candidate_engagement_event
  (tenant_id, candidate_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_ws_candidate_engagement_recruiter
  ON public.ws_candidate_engagement_event
  (tenant_id, recruiter_user_id, occurred_at DESC);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='medlivo_team_api_runtime') THEN
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_protected_action_window TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_candidate_relationship TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT ON public.ws_candidate_engagement_event TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT ON public.ws_business_calendar_exception TO medlivo_team_api_runtime';
  END IF;
END
$$;
