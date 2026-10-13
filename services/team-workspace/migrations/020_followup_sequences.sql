-- Phase 2 recruiter-controlled follow-up sequencing.
CREATE TABLE IF NOT EXISTS public.ws_followup_sequence (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  recruiter_user_id uuid NOT NULL,
  candidate_id uuid NOT NULL,
  job_id uuid,
  status text NOT NULL,
  cadence_days jsonb NOT NULL,
  next_step integer NOT NULL DEFAULT 0,
  stop_on_reply boolean NOT NULL DEFAULT true,
  stopped_reason text,
  started_at timestamptz NOT NULL,
  stopped_at timestamptz,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL,
  CONSTRAINT ws_followup_sequence_recruiter_fk
    FOREIGN KEY (tenant_id,recruiter_user_id) REFERENCES public.app_user(tenant_id,id),
  CONSTRAINT ws_followup_sequence_candidate_fk
    FOREIGN KEY (tenant_id,candidate_id) REFERENCES public.candidate(tenant_id,id),
  CONSTRAINT ws_followup_sequence_job_fk
    FOREIGN KEY (tenant_id,job_id) REFERENCES public.job(tenant_id,id),
  CONSTRAINT ws_followup_sequence_status_ck
    CHECK (status IN ('active','paused','completed','stopped'))
);

CREATE TABLE IF NOT EXISTS public.ws_followup_sequence_step (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  sequence_id uuid NOT NULL,
  step_number integer NOT NULL,
  due_at timestamptz NOT NULL,
  status text NOT NULL,
  outreach_draft_id uuid,
  outreach_execution_id uuid,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL,
  CONSTRAINT ws_followup_sequence_step_sequence_fk
    FOREIGN KEY (sequence_id) REFERENCES public.ws_followup_sequence(id),
  CONSTRAINT ws_followup_sequence_step_draft_fk
    FOREIGN KEY (outreach_draft_id) REFERENCES public.ws_outreach_draft(id),
  CONSTRAINT ws_followup_sequence_step_execution_fk
    FOREIGN KEY (outreach_execution_id) REFERENCES public.ws_outreach_execution(id),
  CONSTRAINT ws_followup_sequence_step_status_ck
    CHECK (status IN ('scheduled','ready_for_review','queued','sent','cancelled','skipped')),
  UNIQUE (tenant_id,sequence_id,step_number)
);

CREATE INDEX IF NOT EXISTS idx_ws_followup_sequence_step_due
  ON public.ws_followup_sequence_step (tenant_id,status,due_at);

CREATE TABLE IF NOT EXISTS public.ws_contact_suppression (
  tenant_id uuid NOT NULL,
  candidate_id uuid NOT NULL,
  channel text NOT NULL,
  reason text NOT NULL,
  source_type text NOT NULL,
  source_reference text,
  created_at timestamptz NOT NULL,
  PRIMARY KEY (tenant_id,candidate_id,channel),
  CONSTRAINT ws_contact_suppression_candidate_fk
    FOREIGN KEY (tenant_id,candidate_id) REFERENCES public.candidate(tenant_id,id),
  CONSTRAINT ws_contact_suppression_channel_ck CHECK (channel IN ('email','sms'))
);

CREATE INDEX IF NOT EXISTS idx_ws_followup_sequence_due
  ON public.ws_followup_sequence (tenant_id,status,updated_at);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='medlivo_team_api_runtime') THEN
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_followup_sequence TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_followup_sequence_step TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON public.ws_contact_suppression TO medlivo_team_api_runtime';
  END IF;
END
$$;
