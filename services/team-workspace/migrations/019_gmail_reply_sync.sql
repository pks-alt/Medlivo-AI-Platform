-- Gmail reply synchronization and recruiter-visible inbound messages.
CREATE TABLE IF NOT EXISTS public.ws_gmail_message (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  recruiter_user_id uuid NOT NULL,
  candidate_id uuid NOT NULL,
  job_id uuid,
  execution_id uuid NOT NULL,
  gmail_message_id text NOT NULL,
  gmail_thread_id text NOT NULL,
  direction text NOT NULL,
  from_address text,
  to_address text,
  subject text,
  body_text text,
  received_at timestamptz NOT NULL,
  history_id text,
  created_at timestamptz NOT NULL,
  CONSTRAINT ws_gmail_message_recruiter_fk
    FOREIGN KEY (tenant_id, recruiter_user_id) REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_gmail_message_candidate_fk
    FOREIGN KEY (tenant_id, candidate_id) REFERENCES public.candidate(tenant_id, id),
  CONSTRAINT ws_gmail_message_job_fk
    FOREIGN KEY (tenant_id, job_id) REFERENCES public.job(tenant_id, id),
  CONSTRAINT ws_gmail_message_execution_fk
    FOREIGN KEY (execution_id) REFERENCES public.ws_outreach_execution(id),
  CONSTRAINT ws_gmail_message_direction_ck CHECK (direction IN ('inbound','outbound')),
  UNIQUE (tenant_id, gmail_message_id)
);

CREATE INDEX IF NOT EXISTS idx_ws_gmail_message_candidate
  ON public.ws_gmail_message (tenant_id, candidate_id, received_at DESC);

CREATE INDEX IF NOT EXISTS idx_ws_gmail_message_recruiter
  ON public.ws_gmail_message (tenant_id, recruiter_user_id, received_at DESC);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='medlivo_team_api_runtime') THEN
    EXECUTE 'GRANT SELECT, INSERT ON public.ws_gmail_message TO medlivo_team_api_runtime';
  END IF;
END
$$;
