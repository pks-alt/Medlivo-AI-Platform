-- Enterprise Phase 1 operational overlays, approvals, provenance and AI review.
-- Apply after 006_job_publication_approval.sql.

CREATE TABLE IF NOT EXISTS public.ws_job_operational_overlay (
  job_id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  team_id uuid,
  recruiter_user_id uuid,
  client_priority text NOT NULL DEFAULT 'normal',
  job_priority text NOT NULL DEFAULT 'standard',
  priority_reason text,
  manager_note text,
  next_action text,
  due_at timestamptz,
  operational_status text NOT NULL DEFAULT 'active',
  version integer NOT NULL DEFAULT 1,
  assigned_by uuid,
  assigned_at timestamptz,
  updated_by uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_job_operational_overlay_job_fk FOREIGN KEY (tenant_id, job_id)
    REFERENCES public.job(tenant_id, id) ON DELETE CASCADE,
  CONSTRAINT ws_job_operational_overlay_team_fk FOREIGN KEY (tenant_id, team_id)
    REFERENCES public.team(tenant_id, id),
  CONSTRAINT ws_job_operational_overlay_recruiter_fk FOREIGN KEY (tenant_id, recruiter_user_id)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_job_operational_overlay_assigned_by_fk FOREIGN KEY (tenant_id, assigned_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_job_operational_overlay_updated_by_fk FOREIGN KEY (tenant_id, updated_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_job_operational_overlay_tenant_job_uq UNIQUE (tenant_id, job_id),
  CONSTRAINT ws_job_operational_overlay_client_priority_ck CHECK (
    client_priority IN ('high','normal','low')
  ),
  CONSTRAINT ws_job_operational_overlay_job_priority_ck CHECK (
    job_priority IN ('hot','priority','standard','hold')
  ),
  CONSTRAINT ws_job_operational_overlay_status_ck CHECK (
    operational_status IN ('active','hold','closed')
  ),
  CONSTRAINT ws_job_operational_overlay_version_ck CHECK (version > 0)
);

CREATE INDEX IF NOT EXISTS idx_ws_job_overlay_team_priority
  ON public.ws_job_operational_overlay(tenant_id, team_id, job_priority, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_ws_job_overlay_recruiter
  ON public.ws_job_operational_overlay(tenant_id, recruiter_user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS public.ws_job_ownership_history (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  job_id uuid NOT NULL,
  previous_owner_user_id uuid,
  new_owner_user_id uuid,
  changed_by uuid NOT NULL,
  reason text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_job_ownership_history_job_fk FOREIGN KEY (tenant_id, job_id)
    REFERENCES public.job(tenant_id, id) ON DELETE CASCADE,
  CONSTRAINT ws_job_ownership_history_previous_fk FOREIGN KEY (tenant_id, previous_owner_user_id)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_job_ownership_history_new_fk FOREIGN KEY (tenant_id, new_owner_user_id)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_job_ownership_history_actor_fk FOREIGN KEY (tenant_id, changed_by)
    REFERENCES public.app_user(tenant_id, id)
);

CREATE INDEX IF NOT EXISTS idx_ws_job_ownership_history_job_created
  ON public.ws_job_ownership_history(tenant_id, job_id, created_at DESC);

CREATE TABLE IF NOT EXISTS public.ws_approval_request (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  approval_type text NOT NULL,
  object_type text NOT NULL,
  object_id uuid NOT NULL,
  requested_by uuid NOT NULL,
  required_authority text NOT NULL,
  status text NOT NULL DEFAULT 'pending',
  reason text,
  decision_notes text,
  decided_by uuid,
  decided_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_approval_request_requested_by_fk FOREIGN KEY (tenant_id, requested_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_approval_request_decided_by_fk FOREIGN KEY (tenant_id, decided_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_approval_request_authority_ck CHECK (
    required_authority IN ('delivery_manager','executive','system_admin')
  ),
  CONSTRAINT ws_approval_request_status_ck CHECK (
    status IN ('pending','approved','rejected','cancelled')
  )
);

CREATE INDEX IF NOT EXISTS idx_ws_approval_request_status
  ON public.ws_approval_request(tenant_id, status, required_authority, created_at DESC);

CREATE TABLE IF NOT EXISTS public.ws_provenance (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  object_type text NOT NULL,
  object_id uuid NOT NULL,
  field_path text NOT NULL,
  source_type text NOT NULL,
  source_reference text,
  confidence numeric(5,4),
  value_payload jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_provenance_confidence_ck CHECK (
    confidence IS NULL OR (confidence >= 0 AND confidence <= 1)
  )
);

CREATE INDEX IF NOT EXISTS idx_ws_provenance_object
  ON public.ws_provenance(tenant_id, object_type, object_id, field_path);

CREATE TABLE IF NOT EXISTS public.ws_ai_suggestion (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  object_type text NOT NULL,
  object_id uuid NOT NULL,
  field_path text NOT NULL,
  suggested_value jsonb NOT NULL,
  source_basis jsonb NOT NULL DEFAULT '[]'::jsonb,
  confidence numeric(5,4),
  model_provider text,
  model_version text,
  policy_version text,
  status text NOT NULL DEFAULT 'proposed',
  reviewed_by uuid,
  reviewed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_ai_suggestion_reviewer_fk FOREIGN KEY (tenant_id, reviewed_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_ai_suggestion_confidence_ck CHECK (
    confidence IS NULL OR (confidence >= 0 AND confidence <= 1)
  ),
  CONSTRAINT ws_ai_suggestion_status_ck CHECK (
    status IN ('proposed','accepted','modified','rejected','expired')
  )
);

CREATE INDEX IF NOT EXISTS idx_ws_ai_suggestion_object_status
  ON public.ws_ai_suggestion(tenant_id, object_type, object_id, status, created_at DESC);

CREATE TABLE IF NOT EXISTS public.ws_operational_audit (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  actor_user_id uuid NOT NULL,
  action text NOT NULL,
  object_type text NOT NULL,
  object_id uuid NOT NULL,
  before_state jsonb NOT NULL DEFAULT '{}'::jsonb,
  after_state jsonb NOT NULL DEFAULT '{}'::jsonb,
  reason text,
  correlation_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_operational_audit_actor_fk FOREIGN KEY (tenant_id, actor_user_id)
    REFERENCES public.app_user(tenant_id, id)
);

CREATE INDEX IF NOT EXISTS idx_ws_operational_audit_object_created
  ON public.ws_operational_audit(tenant_id, object_type, object_id, created_at DESC);

ALTER TABLE public.ws_job_intake_batch
  ADD COLUMN IF NOT EXISTS source_file_hash text,
  ADD COLUMN IF NOT EXISTS ai_processing_status text NOT NULL DEFAULT 'not_started',
  ADD COLUMN IF NOT EXISTS review_owner_user_id uuid,
  ADD COLUMN IF NOT EXISTS approved_by uuid,
  ADD COLUMN IF NOT EXISTS approved_at timestamptz,
  ADD COLUMN IF NOT EXISTS correlation_id uuid;

ALTER TABLE public.ws_job_intake_item
  ADD COLUMN IF NOT EXISTS extracted_values jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS ai_suggestions jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS conflicts jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS missing_fields jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS final_approved_values jsonb,
  ADD COLUMN IF NOT EXISTS bill_rate_state text NOT NULL DEFAULT 'unknown',
  ADD COLUMN IF NOT EXISTS recruiting_readiness text NOT NULL DEFAULT 'review',
  ADD COLUMN IF NOT EXISTS commercial_readiness text NOT NULL DEFAULT 'review',
  ADD COLUMN IF NOT EXISTS reviewed_by uuid,
  ADD COLUMN IF NOT EXISTS reviewed_at timestamptz;

ALTER TABLE public.ws_customer_job_mapping
  ADD COLUMN IF NOT EXISTS mapping_version integer NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS approved_by uuid,
  ADD COLUMN IF NOT EXISTS effective_from timestamptz,
  ADD COLUMN IF NOT EXISTS is_active boolean NOT NULL DEFAULT true;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname='ws_job_intake_batch_review_owner_fk'
  ) THEN
    ALTER TABLE public.ws_job_intake_batch
      ADD CONSTRAINT ws_job_intake_batch_review_owner_fk
      FOREIGN KEY (tenant_id, review_owner_user_id) REFERENCES public.app_user(tenant_id, id);
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname='ws_job_intake_batch_approved_by_fk'
  ) THEN
    ALTER TABLE public.ws_job_intake_batch
      ADD CONSTRAINT ws_job_intake_batch_approved_by_fk
      FOREIGN KEY (tenant_id, approved_by) REFERENCES public.app_user(tenant_id, id);
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname='ws_job_intake_item_reviewed_by_fk'
  ) THEN
    ALTER TABLE public.ws_job_intake_item
      ADD CONSTRAINT ws_job_intake_item_reviewed_by_fk
      FOREIGN KEY (tenant_id, reviewed_by) REFERENCES public.app_user(tenant_id, id);
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname='ws_customer_job_mapping_approved_by_fk'
  ) THEN
    ALTER TABLE public.ws_customer_job_mapping
      ADD CONSTRAINT ws_customer_job_mapping_approved_by_fk
      FOREIGN KEY (tenant_id, approved_by) REFERENCES public.app_user(tenant_id, id);
  END IF;
END
$$;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='medlivo_team_api_runtime') THEN
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_job_operational_overlay TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT ON public.ws_job_ownership_history TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_approval_request TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_provenance TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_ai_suggestion TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT ON public.ws_operational_audit TO medlivo_team_api_runtime';
  END IF;
END
$$;
