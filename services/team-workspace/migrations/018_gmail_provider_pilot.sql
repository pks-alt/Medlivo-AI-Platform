-- Phase 2 Gmail provider pilot.
-- Individual recruiter OAuth only. Refresh tokens are stored in Google Secret Manager,
-- never in this database. Gmail send remains limited to approved outreach executions.

ALTER TABLE public.ws_outreach_execution
  ADD COLUMN IF NOT EXISTS provider_thread_id text;

CREATE TABLE IF NOT EXISTS public.ws_gmail_connection (
  tenant_id uuid NOT NULL,
  recruiter_user_id uuid NOT NULL,
  gmail_address text NOT NULL,
  status text NOT NULL,
  refresh_token_secret_resource text NOT NULL,
  granted_scopes jsonb NOT NULL DEFAULT '[]'::jsonb,
  history_id text,
  watch_expiration timestamptz,
  connected_at timestamptz NOT NULL,
  last_sync_at timestamptz,
  disconnected_at timestamptz,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL,
  PRIMARY KEY (tenant_id, recruiter_user_id),
  CONSTRAINT ws_gmail_connection_recruiter_fk
    FOREIGN KEY (tenant_id, recruiter_user_id) REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_gmail_connection_status_ck
    CHECK (status IN ('connected','reauthorization_required','disconnected'))
);

CREATE TABLE IF NOT EXISTS public.ws_gmail_oauth_state (
  state_hash text PRIMARY KEY,
  tenant_id uuid NOT NULL,
  recruiter_user_id uuid NOT NULL,
  expires_at timestamptz NOT NULL,
  consumed_at timestamptz,
  created_at timestamptz NOT NULL,
  CONSTRAINT ws_gmail_oauth_state_recruiter_fk
    FOREIGN KEY (tenant_id, recruiter_user_id) REFERENCES public.app_user(tenant_id, id)
);

CREATE INDEX IF NOT EXISTS idx_ws_gmail_connection_status
  ON public.ws_gmail_connection (tenant_id, status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_ws_gmail_oauth_state_user
  ON public.ws_gmail_oauth_state (tenant_id, recruiter_user_id, expires_at DESC);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='medlivo_team_api_runtime') THEN
    EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON public.ws_gmail_connection TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON public.ws_gmail_oauth_state TO medlivo_team_api_runtime';
  END IF;
END
$$;
