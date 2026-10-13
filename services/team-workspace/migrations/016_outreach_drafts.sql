-- Recruiter-controlled AI outreach drafts. This migration does not enable external sending.
CREATE TABLE IF NOT EXISTS public.ws_outreach_draft (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  candidate_id uuid NOT NULL,
  job_id uuid,
  recruiter_user_id uuid NOT NULL,
  channel text NOT NULL,
  purpose text NOT NULL,
  status text NOT NULL,
  subject text,
  body text NOT NULL,
  warnings jsonb NOT NULL DEFAULT '[]'::jsonb,
  source_context jsonb NOT NULL DEFAULT '{}'::jsonb,
  model_provider text,
  model_version text,
  policy_version text NOT NULL,
  approved_by uuid,
  approved_at timestamptz,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL,
  CONSTRAINT ws_outreach_draft_candidate_fk
    FOREIGN KEY (tenant_id, candidate_id) REFERENCES public.candidate(tenant_id, id),
  CONSTRAINT ws_outreach_draft_job_fk
    FOREIGN KEY (tenant_id, job_id) REFERENCES public.job(tenant_id, id),
  CONSTRAINT ws_outreach_draft_recruiter_fk
    FOREIGN KEY (tenant_id, recruiter_user_id) REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_outreach_draft_approver_fk
    FOREIGN KEY (tenant_id, approved_by) REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_outreach_draft_channel_ck CHECK (channel IN ('email','sms')),
  CONSTRAINT ws_outreach_draft_purpose_ck CHECK (
    purpose IN ('initial_outreach','follow_up','availability_reconfirm','interview_followup','pay_followup','next_step')
  ),
  CONSTRAINT ws_outreach_draft_status_ck CHECK (status IN ('draft','approved','cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_ws_outreach_draft_recruiter
  ON public.ws_outreach_draft (tenant_id, recruiter_user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ws_outreach_draft_candidate
  ON public.ws_outreach_draft (tenant_id, candidate_id, created_at DESC);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='medlivo_team_api_runtime') THEN
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_outreach_draft TO medlivo_team_api_runtime';
  END IF;
END
$$;
