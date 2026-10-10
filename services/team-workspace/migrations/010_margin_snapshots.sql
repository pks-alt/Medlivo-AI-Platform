-- Phase 1 Margin snapshots, guideline discussions, and hard-exception support.
-- Apply after 009_enterprise_rbac.sql.

CREATE TABLE IF NOT EXISTS public.ws_cost_assumption_set (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  profile text NOT NULL,
  version text NOT NULL,
  assumption_payload jsonb NOT NULL,
  status text NOT NULL DEFAULT 'active',
  effective_from timestamptz NOT NULL,
  effective_to timestamptz,
  created_by uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_cost_assumption_user_fk FOREIGN KEY (tenant_id, created_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_cost_assumption_status_ck CHECK (status IN ('active','retired')),
  CONSTRAINT ws_cost_assumption_uq UNIQUE (tenant_id, profile, version)
);

CREATE TABLE IF NOT EXISTS public.ws_margin_snapshot (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  job_id uuid NOT NULL,
  candidate_id uuid NOT NULL,
  recruiter_user_id uuid NOT NULL,
  calculation_profile text NOT NULL,
  assumption_set_id uuid NOT NULL,
  assumption_version text NOT NULL,
  version integer NOT NULL,
  input_payload jsonb NOT NULL,
  result_payload jsonb NOT NULL,
  guideline_status text NOT NULL,
  lifecycle_status text NOT NULL DEFAULT 'draft',
  created_by uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  finalized_by uuid,
  finalized_at timestamptz,
  CONSTRAINT ws_margin_snapshot_job_fk FOREIGN KEY (tenant_id, job_id)
    REFERENCES public.job(tenant_id, id),
  CONSTRAINT ws_margin_snapshot_candidate_fk FOREIGN KEY (tenant_id, candidate_id)
    REFERENCES public.candidate(tenant_id, id),
  CONSTRAINT ws_margin_snapshot_recruiter_fk FOREIGN KEY (tenant_id, recruiter_user_id)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_margin_snapshot_created_by_fk FOREIGN KEY (tenant_id, created_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_margin_snapshot_finalized_by_fk FOREIGN KEY (tenant_id, finalized_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_margin_snapshot_assumption_fk FOREIGN KEY (assumption_set_id)
    REFERENCES public.ws_cost_assumption_set(id),
  CONSTRAINT ws_margin_snapshot_guideline_ck CHECK (
    guideline_status IN (
      'within_guideline','discuss_delivery_manager','discuss_leadership',
      'negative_gm','policy_unconfigured'
    )
  ),
  CONSTRAINT ws_margin_snapshot_lifecycle_ck CHECK (
    lifecycle_status IN ('draft','finalized','superseded','hard_exception_required')
  ),
  CONSTRAINT ws_margin_snapshot_version_ck CHECK (version > 0),
  CONSTRAINT ws_margin_snapshot_uq UNIQUE (tenant_id, job_id, candidate_id, version)
);

CREATE INDEX IF NOT EXISTS idx_ws_margin_snapshot_job_candidate
  ON public.ws_margin_snapshot(tenant_id, job_id, candidate_id, version DESC);

CREATE TABLE IF NOT EXISTS public.ws_margin_cost_component (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  snapshot_id uuid NOT NULL,
  component_key text NOT NULL,
  label text NOT NULL,
  category text NOT NULL,
  per_week numeric(18,6) NOT NULL,
  assignment_total numeric(18,6) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_margin_component_snapshot_fk FOREIGN KEY (snapshot_id)
    REFERENCES public.ws_margin_snapshot(id) ON DELETE CASCADE,
  CONSTRAINT ws_margin_component_uq UNIQUE (snapshot_id, component_key)
);

CREATE TABLE IF NOT EXISTS public.ws_margin_discussion (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  snapshot_id uuid NOT NULL,
  recorded_by uuid NOT NULL,
  participant_user_id uuid,
  participant_role text NOT NULL,
  discussion_type text NOT NULL,
  notes text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_margin_discussion_snapshot_fk FOREIGN KEY (snapshot_id)
    REFERENCES public.ws_margin_snapshot(id) ON DELETE CASCADE,
  CONSTRAINT ws_margin_discussion_actor_fk FOREIGN KEY (tenant_id, recorded_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_margin_discussion_participant_fk FOREIGN KEY (tenant_id, participant_user_id)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_margin_discussion_role_ck CHECK (
    participant_role IN ('delivery_manager','executive','designated_leadership')
  ),
  CONSTRAINT ws_margin_discussion_type_ck CHECK (
    discussion_type IN ('rate_guidance','commercial_exception','leadership_exception')
  )
);

CREATE INDEX IF NOT EXISTS idx_ws_margin_discussion_snapshot
  ON public.ws_margin_discussion(tenant_id, snapshot_id, created_at);

CREATE TABLE IF NOT EXISTS public.ws_commission_projection (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  snapshot_id uuid NOT NULL UNIQUE,
  recruiter_user_id uuid NOT NULL,
  commissionable_net_profit numeric(18,6) NOT NULL,
  commission_rate numeric(12,10) NOT NULL,
  projected_amount numeric(18,6) NOT NULL,
  status text NOT NULL DEFAULT 'projected',
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_commission_snapshot_fk FOREIGN KEY (snapshot_id)
    REFERENCES public.ws_margin_snapshot(id) ON DELETE CASCADE,
  CONSTRAINT ws_commission_recruiter_fk FOREIGN KEY (tenant_id, recruiter_user_id)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_commission_status_ck CHECK (
    status IN ('projected','approved','earned','cancelled')
  )
);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='medlivo_team_api_runtime') THEN
    EXECUTE 'GRANT SELECT, INSERT ON public.ws_cost_assumption_set TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_margin_snapshot TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT ON public.ws_margin_cost_component TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT ON public.ws_margin_discussion TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT ON public.ws_commission_projection TO medlivo_team_api_runtime';
  END IF;
END
$$;
