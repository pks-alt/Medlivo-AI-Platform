-- AI-native Submission Studio foundation.
-- Templates govern customer/MSP requirements; packages capture the exact version used.

CREATE TABLE IF NOT EXISTS public.ws_submission_template (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  name text NOT NULL,
  division text NOT NULL,
  customer_id uuid,
  program_name text,
  profession text,
  specialty text,
  template_scope text NOT NULL,
  version integer NOT NULL,
  status text NOT NULL DEFAULT 'draft',
  effective_from timestamptz,
  effective_to timestamptz,
  parent_template_id uuid,
  resume_format_profile jsonb NOT NULL DEFAULT '{}'::jsonb,
  output_profile jsonb NOT NULL DEFAULT '{}'::jsonb,
  ai_policy jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_submission_template_scope_ck CHECK (
    template_scope IN ('medlivo_default','division_default','customer','program','profession','specialty','job')
  ),
  CONSTRAINT ws_submission_template_status_ck CHECK (
    status IN ('draft','active','retired')
  ),
  CONSTRAINT ws_submission_template_version_ck CHECK (version > 0),
  CONSTRAINT ws_submission_template_customer_fk FOREIGN KEY (tenant_id, customer_id)
    REFERENCES public.customer(tenant_id, id),
  CONSTRAINT ws_submission_template_creator_fk FOREIGN KEY (tenant_id, created_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_submission_template_parent_fk FOREIGN KEY (parent_template_id)
    REFERENCES public.ws_submission_template(id)
);

CREATE TABLE IF NOT EXISTS public.ws_submission_template_requirement (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  template_id uuid NOT NULL,
  requirement_key text NOT NULL,
  label text NOT NULL,
  requirement_type text NOT NULL,
  category text NOT NULL,
  lifecycle_stage text NOT NULL DEFAULT 'submission',
  sensitivity text NOT NULL DEFAULT 'internal',
  fulfillment_strategy text NOT NULL DEFAULT 'source_or_ai',
  required boolean NOT NULL DEFAULT true,
  source_preference jsonb NOT NULL DEFAULT '[]'::jsonb,
  validation_rule jsonb NOT NULL DEFAULT '{}'::jsonb,
  output_rule jsonb NOT NULL DEFAULT '{}'::jsonb,
  display_order integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_submission_template_requirement_type_ck CHECK (
    requirement_type IN ('field','document','derived','attestation','form','reference','skills_checklist')
  ),
  CONSTRAINT ws_submission_template_requirement_stage_ck CHECK (
    lifecycle_stage IN ('submission','credentialing','start')
  ),
  CONSTRAINT ws_submission_template_requirement_sensitivity_ck CHECK (
    sensitivity IN ('standard','internal','confidential','restricted')
  ),
  CONSTRAINT ws_submission_template_requirement_fulfillment_ck CHECK (
    fulfillment_strategy IN ('source_only','source_or_ai','derived','manual_confirmation')
  ),
  CONSTRAINT ws_submission_template_requirement_uq UNIQUE (template_id, requirement_key),
  CONSTRAINT ws_submission_template_requirement_template_fk FOREIGN KEY (template_id)
    REFERENCES public.ws_submission_template(id)
);

CREATE TABLE IF NOT EXISTS public.ws_candidate_document_asset (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  candidate_id uuid NOT NULL,
  document_type text NOT NULL,
  title text NOT NULL,
  source_system text,
  source_reference text,
  storage_reference text,
  issue_date date,
  expiration_date date,
  verified_status text NOT NULL DEFAULT 'unverified',
  verified_source text,
  extracted_facts jsonb NOT NULL DEFAULT '{}'::jsonb,
  ai_classification jsonb NOT NULL DEFAULT '{}'::jsonb,
  content_hash text,
  is_current boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_candidate_document_asset_verified_ck CHECK (
    verified_status IN ('unverified','verified','conflict','expired','rejected')
  ),
  CONSTRAINT ws_candidate_document_asset_candidate_fk FOREIGN KEY (tenant_id, candidate_id)
    REFERENCES public.candidate(tenant_id, id)
);

CREATE TABLE IF NOT EXISTS public.ws_submission_package (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  job_id uuid NOT NULL,
  candidate_id uuid NOT NULL,
  recruiter_user_id uuid NOT NULL,
  template_id uuid NOT NULL,
  template_version integer NOT NULL,
  status text NOT NULL DEFAULT 'draft',
  readiness_status text NOT NULL DEFAULT 'needs_review',
  readiness_score numeric(5,2) NOT NULL DEFAULT 0,
  ai_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  validation_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  recruiter_edits jsonb NOT NULL DEFAULT '{}'::jsonb,
  generated_artifacts jsonb NOT NULL DEFAULT '[]'::jsonb,
  version integer NOT NULL DEFAULT 1,
  finalized_at timestamptz,
  finalized_by uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_submission_package_status_ck CHECK (
    status IN ('draft','ai_prepared','needs_review','ready_to_submit','finalized','superseded')
  ),
  CONSTRAINT ws_submission_package_readiness_ck CHECK (
    readiness_status IN ('not_started','missing_required','needs_review','ready')
  ),
  CONSTRAINT ws_submission_package_version_ck CHECK (version > 0),
  CONSTRAINT ws_submission_package_job_fk FOREIGN KEY (tenant_id, job_id)
    REFERENCES public.job(tenant_id, id),
  CONSTRAINT ws_submission_package_candidate_fk FOREIGN KEY (tenant_id, candidate_id)
    REFERENCES public.candidate(tenant_id, id),
  CONSTRAINT ws_submission_package_recruiter_fk FOREIGN KEY (tenant_id, recruiter_user_id)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_submission_package_template_fk FOREIGN KEY (template_id)
    REFERENCES public.ws_submission_template(id),
  CONSTRAINT ws_submission_package_finalizer_fk FOREIGN KEY (tenant_id, finalized_by)
    REFERENCES public.app_user(tenant_id, id)
);

CREATE TABLE IF NOT EXISTS public.ws_submission_package_item (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  package_id uuid NOT NULL,
  requirement_id uuid NOT NULL,
  requirement_key text NOT NULL,
  label text NOT NULL,
  item_type text NOT NULL,
  status text NOT NULL,
  source_type text,
  source_reference text,
  document_asset_id uuid,
  resolved_value jsonb,
  ai_confidence numeric(5,4),
  conflict_detail jsonb,
  recruiter_note text,
  display_order integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_submission_package_item_status_ck CHECK (
    status IN ('missing','ai_filled','matched','conflict','needs_review','approved','waived','not_applicable')
  ),
  CONSTRAINT ws_submission_package_item_package_fk FOREIGN KEY (package_id)
    REFERENCES public.ws_submission_package(id),
  CONSTRAINT ws_submission_package_item_requirement_fk FOREIGN KEY (requirement_id)
    REFERENCES public.ws_submission_template_requirement(id),
  CONSTRAINT ws_submission_package_item_document_fk FOREIGN KEY (document_asset_id)
    REFERENCES public.ws_candidate_document_asset(id)
);

CREATE TABLE IF NOT EXISTS public.ws_submission_validation_result (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  package_id uuid NOT NULL,
  severity text NOT NULL,
  code text NOT NULL,
  field_key text,
  message text NOT NULL,
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  resolution_status text NOT NULL DEFAULT 'open',
  resolved_by uuid,
  resolved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_submission_validation_severity_ck CHECK (
    severity IN ('info','warning','blocking')
  ),
  CONSTRAINT ws_submission_validation_resolution_ck CHECK (
    resolution_status IN ('open','accepted','corrected','waived')
  ),
  CONSTRAINT ws_submission_validation_package_fk FOREIGN KEY (package_id)
    REFERENCES public.ws_submission_package(id),
  CONSTRAINT ws_submission_validation_resolver_fk FOREIGN KEY (tenant_id, resolved_by)
    REFERENCES public.app_user(tenant_id, id)
);

CREATE INDEX IF NOT EXISTS idx_ws_submission_template_match
  ON public.ws_submission_template(tenant_id, division, customer_id, program_name, profession, specialty, status);
CREATE INDEX IF NOT EXISTS idx_ws_candidate_document_asset_candidate
  ON public.ws_candidate_document_asset(tenant_id, candidate_id, document_type, is_current);
CREATE INDEX IF NOT EXISTS idx_ws_submission_package_pair
  ON public.ws_submission_package(tenant_id, job_id, candidate_id, version DESC);
CREATE INDEX IF NOT EXISTS idx_ws_submission_package_status
  ON public.ws_submission_package(tenant_id, readiness_status, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_ws_submission_package_item_status
  ON public.ws_submission_package_item(tenant_id, package_id, status, display_order);
CREATE INDEX IF NOT EXISTS idx_ws_submission_validation_open
  ON public.ws_submission_validation_result(tenant_id, package_id, resolution_status, severity);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='medlivo_team_api_runtime') THEN
    EXECUTE 'GRANT SELECT ON public.ws_submission_template TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT ON public.ws_submission_template_requirement TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_candidate_document_asset TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_submission_package TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_submission_package_item TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_submission_validation_result TO medlivo_team_api_runtime';
  END IF;
END
$$;
