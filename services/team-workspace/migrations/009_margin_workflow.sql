-- Phase 1 Margin & Cost Engine persistence and approval workflow.
-- Apply after 008_intake_intelligence.sql.

CREATE TABLE IF NOT EXISTS public.ws_cost_assumption_set (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  profile text NOT NULL,
  version text NOT NULL,
  assumption_payload jsonb NOT NULL,
  effective_from timestamptz NOT NULL,
  effective_to timestamptz,
  status text NOT NULL DEFAULT 'active',
  approved_by uuid,
  created_by uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_cost_assumption_set_tenant_fk FOREIGN KEY (tenant_id)
    REFERENCES public.tenant(id),
  CONSTRAINT ws_cost_assumption_set_approved_by_fk FOREIGN KEY (tenant_id, approved_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_cost_assumption_set_created_by_fk FOREIGN KEY (tenant_id, created_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_cost_assumption_set_status_ck CHECK (status IN ('draft','active','retired')),
  CONSTRAINT ws_cost_assumption_set_uq UNIQUE (tenant_id, profile, version)
);

CREATE INDEX IF NOT EXISTS idx_ws_cost_assumption_profile_effective
  ON public.ws_cost_assumption_set(tenant_id, profile, effective_from DESC);

CREATE TABLE IF NOT EXISTS public.ws_margin_snapshot (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  job_id uuid NOT NULL,
  candidate_id uuid NOT NULL,
  recruiter_user_id uuid NOT NULL,
  profile text NOT NULL,
  assumption_set_id uuid,
  assumption_version text NOT NULL,
  version integer NOT NULL,
  input_payload jsonb NOT NULL,
  result_payload jsonb NOT NULL,
  approval_status text NOT NULL,
  lifecycle_status text NOT NULL DEFAULT 'draft',
  created_by uuid NOT NULL,
  finalized_by uuid,
  finalized_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
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
  CONSTRAINT ws_margin_snapshot_version_ck CHECK (version > 0),
  CONSTRAINT ws_margin_snapshot_lifecycle_ck CHECK (
    lifecycle_status IN ('draft','negotiated','approval_required','approved','finalized','superseded')
  ),
  CONSTRAINT ws_margin_snapshot_approval_ck CHECK (
    approval_status IN (
      'healthy','manager_approval_required','executive_approval_required',
      'negative_gm','policy_unconfigured'
    )
  ),
  CONSTRAINT ws_margin_snapshot_job_candidate_version_uq
    UNIQUE (tenant_id, job_id, candidate_id, version)
);

CREATE INDEX IF NOT EXISTS idx_ws_margin_snapshot_job_candidate
  ON public.ws_margin_snapshot(tenant_id, job_id, candidate_id, version DESC);

CREATE INDEX IF NOT EXISTS idx_ws_margin_snapshot_recruiter
  ON public.ws_margin_snapshot(tenant_id, recruiter_user_id, created_at DESC);

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
  CONSTRAINT ws_margin_cost_component_snapshot_fk FOREIGN KEY (snapshot_id)
    REFERENCES public.ws_margin_snapshot(id) ON DELETE CASCADE,
  CONSTRAINT ws_margin_cost_component_category_ck CHECK (
    category IN ('revenue_reduction','recurring_cost','one_time_cost')
  ),
  CONSTRAINT ws_margin_cost_component_uq UNIQUE (snapshot_id, component_key)
);

CREATE INDEX IF NOT EXISTS idx_ws_margin_component_snapshot
  ON public.ws_margin_cost_component(snapshot_id, component_key);

CREATE TABLE IF NOT EXISTS public.ws_commission_projection (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  snapshot_id uuid NOT NULL,
  recruiter_user_id uuid NOT NULL,
  commissionable_net_profit numeric(18,6) NOT NULL,
  commission_rate numeric(12,10) NOT NULL,
  projected_amount numeric(18,6) NOT NULL,
  status text NOT NULL DEFAULT 'projected',
  quarter text,
  approved_amount numeric(18,6),
  approved_by uuid,
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_commission_projection_snapshot_fk FOREIGN KEY (snapshot_id)
    REFERENCES public.ws_margin_snapshot(id) ON DELETE CASCADE,
  CONSTRAINT ws_commission_projection_recruiter_fk FOREIGN KEY (tenant_id, recruiter_user_id)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_commission_projection_approved_by_fk FOREIGN KEY (tenant_id, approved_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_commission_projection_status_ck CHECK (
    status IN ('projected','approved','earned','cancelled')
  ),
  CONSTRAINT ws_commission_projection_snapshot_uq UNIQUE (snapshot_id)
);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='medlivo_team_api_runtime') THEN
    EXECUTE 'GRANT SELECT ON public.ws_cost_assumption_set TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_margin_snapshot TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT ON public.ws_margin_cost_component TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_commission_projection TO medlivo_team_api_runtime';
  END IF;
END
$$;
