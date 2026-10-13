-- Phase 2 guarded outreach execution queue.
-- Creates an auditable queue between recruiter-approved drafts and external providers.
-- Provider workers remain separately deployable; no JobDiva writeback is introduced here.

CREATE TABLE IF NOT EXISTS public.ws_outreach_execution (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  draft_id uuid NOT NULL,
  candidate_id uuid NOT NULL,
  job_id uuid,
  recruiter_user_id uuid NOT NULL,
  channel text NOT NULL,
  provider text NOT NULL,
  status text NOT NULL,
  scheduled_for timestamptz NOT NULL,
  claimed_at timestamptz,
  sent_at timestamptz,
  failed_at timestamptz,
  attempt_count integer NOT NULL DEFAULT 0,
  max_attempts integer NOT NULL DEFAULT 3,
  provider_message_id text,
  last_error text,
  payload_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL,
  CONSTRAINT ws_outreach_execution_draft_fk
    FOREIGN KEY (draft_id) REFERENCES public.ws_outreach_draft(id),
  CONSTRAINT ws_outreach_execution_candidate_fk
    FOREIGN KEY (tenant_id, candidate_id) REFERENCES public.candidate(tenant_id, id),
  CONSTRAINT ws_outreach_execution_job_fk
    FOREIGN KEY (tenant_id, job_id) REFERENCES public.job(tenant_id, id),
  CONSTRAINT ws_outreach_execution_recruiter_fk
    FOREIGN KEY (tenant_id, recruiter_user_id) REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_outreach_execution_channel_ck CHECK (channel IN ('email','sms')),
  CONSTRAINT ws_outreach_execution_provider_ck CHECK (provider IN ('gmail','zoom_phone')),
  CONSTRAINT ws_outreach_execution_status_ck CHECK (
    status IN ('queued','processing','sent','failed','cancelled')
  ),
  CONSTRAINT ws_outreach_execution_attempt_ck CHECK (
    attempt_count >= 0 AND max_attempts BETWEEN 1 AND 10
  ),
  CONSTRAINT ws_outreach_execution_terminal_ck CHECK (
    (status='sent' AND sent_at IS NOT NULL)
    OR status<>'sent'
  ),
  UNIQUE (tenant_id, draft_id)
);

CREATE INDEX IF NOT EXISTS idx_ws_outreach_execution_queue
  ON public.ws_outreach_execution (tenant_id, status, scheduled_for, created_at);

CREATE INDEX IF NOT EXISTS idx_ws_outreach_execution_recruiter
  ON public.ws_outreach_execution (tenant_id, recruiter_user_id, created_at DESC);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='medlivo_team_api_runtime') THEN
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_outreach_execution TO medlivo_team_api_runtime';
  END IF;
END
$$;
