-- Phase 1 operations: direct-customer job intake and weekly recruiter review.
-- Apply after 004_admin_user_management.sql.

CREATE TABLE IF NOT EXISTS public.ws_job_intake_batch (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  team_id uuid,
  uploaded_by uuid NOT NULL,
  customer_name text NOT NULL,
  division text NOT NULL,
  source_filename text NOT NULL,
  status text NOT NULL DEFAULT 'draft',
  mapping jsonb NOT NULL DEFAULT '{}'::jsonb,
  row_count integer NOT NULL DEFAULT 0,
  ready_count integer NOT NULL DEFAULT 0,
  review_count integer NOT NULL DEFAULT 0,
  duplicate_count integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_job_intake_batch_tenant_fk FOREIGN KEY (tenant_id)
    REFERENCES public.tenant(id),
  CONSTRAINT ws_job_intake_batch_team_fk FOREIGN KEY (tenant_id, team_id)
    REFERENCES public.team(tenant_id, id),
  CONSTRAINT ws_job_intake_batch_user_fk FOREIGN KEY (tenant_id, uploaded_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_job_intake_batch_status_ck CHECK (
    status IN ('draft','review','approved','syncing','synced','failed','cancelled')
  ),
  CONSTRAINT ws_job_intake_batch_counts_ck CHECK (
    row_count >= 0 AND ready_count >= 0 AND review_count >= 0 AND duplicate_count >= 0
    AND ready_count + review_count + duplicate_count <= row_count
  )
);

CREATE INDEX IF NOT EXISTS idx_ws_job_intake_batch_team_created
  ON public.ws_job_intake_batch(tenant_id, team_id, created_at DESC, id);

CREATE TABLE IF NOT EXISTS public.ws_job_intake_item (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  batch_id uuid NOT NULL,
  row_number integer NOT NULL,
  source_row jsonb NOT NULL,
  normalized_job jsonb NOT NULL,
  validation_errors jsonb NOT NULL DEFAULT '[]'::jsonb,
  duplicate_job_id uuid,
  status text NOT NULL DEFAULT 'review',
  created_job_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_job_intake_item_batch_fk FOREIGN KEY (tenant_id, batch_id)
    REFERENCES public.ws_job_intake_batch(tenant_id, id) ON DELETE CASCADE,
  CONSTRAINT ws_job_intake_item_duplicate_fk FOREIGN KEY (tenant_id, duplicate_job_id)
    REFERENCES public.job(tenant_id, id),
  CONSTRAINT ws_job_intake_item_created_job_fk FOREIGN KEY (tenant_id, created_job_id)
    REFERENCES public.job(tenant_id, id),
  CONSTRAINT ws_job_intake_item_status_ck CHECK (
    status IN ('ready','review','duplicate','approved','synced','rejected','failed')
  ),
  CONSTRAINT ws_job_intake_item_row_ck CHECK (row_number > 0),
  CONSTRAINT ws_job_intake_item_batch_row_uq UNIQUE (tenant_id, batch_id, row_number)
);

CREATE INDEX IF NOT EXISTS idx_ws_job_intake_item_batch_status
  ON public.ws_job_intake_item(tenant_id, batch_id, status, row_number);

CREATE TABLE IF NOT EXISTS public.ws_customer_job_mapping (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  customer_name text NOT NULL,
  division text NOT NULL,
  mapping jsonb NOT NULL,
  updated_by uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_customer_job_mapping_tenant_fk FOREIGN KEY (tenant_id)
    REFERENCES public.tenant(id),
  CONSTRAINT ws_customer_job_mapping_user_fk FOREIGN KEY (tenant_id, updated_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_customer_job_mapping_uq UNIQUE (tenant_id, customer_name, division)
);

CREATE TABLE IF NOT EXISTS public.ws_weekly_recruiter_goal (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  team_id uuid NOT NULL,
  recruiter_user_id uuid NOT NULL,
  week_start date NOT NULL,
  submissions_target integer NOT NULL DEFAULT 0,
  interviews_target integer NOT NULL DEFAULT 0,
  closures_target integer NOT NULL DEFAULT 0,
  priority_jobs_target integer NOT NULL DEFAULT 0,
  notes text,
  created_by uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_weekly_goal_team_fk FOREIGN KEY (tenant_id, team_id)
    REFERENCES public.team(tenant_id, id),
  CONSTRAINT ws_weekly_goal_recruiter_fk FOREIGN KEY (tenant_id, recruiter_user_id)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_weekly_goal_creator_fk FOREIGN KEY (tenant_id, created_by)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_weekly_goal_nonnegative_ck CHECK (
    submissions_target >= 0 AND interviews_target >= 0
    AND closures_target >= 0 AND priority_jobs_target >= 0
  ),
  CONSTRAINT ws_weekly_goal_uq UNIQUE (tenant_id, recruiter_user_id, week_start)
);

CREATE INDEX IF NOT EXISTS idx_ws_weekly_goal_team_week
  ON public.ws_weekly_recruiter_goal(tenant_id, team_id, week_start DESC, recruiter_user_id);

CREATE TABLE IF NOT EXISTS public.ws_weekly_recruiter_snapshot (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  team_id uuid NOT NULL,
  recruiter_user_id uuid NOT NULL,
  week_start date NOT NULL,
  submissions_actual integer NOT NULL DEFAULT 0,
  interviews_actual integer NOT NULL DEFAULT 0,
  closures_actual integer NOT NULL DEFAULT 0,
  offers_actual integer NOT NULL DEFAULT 0,
  starts_actual integer NOT NULL DEFAULT 0,
  qualified_actual integer NOT NULL DEFAULT 0,
  responses_actual integer NOT NULL DEFAULT 0,
  source_breakdown jsonb NOT NULL DEFAULT '{}'::jsonb,
  generated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ws_weekly_snapshot_team_fk FOREIGN KEY (tenant_id, team_id)
    REFERENCES public.team(tenant_id, id),
  CONSTRAINT ws_weekly_snapshot_recruiter_fk FOREIGN KEY (tenant_id, recruiter_user_id)
    REFERENCES public.app_user(tenant_id, id),
  CONSTRAINT ws_weekly_snapshot_nonnegative_ck CHECK (
    submissions_actual >= 0 AND interviews_actual >= 0 AND closures_actual >= 0
    AND offers_actual >= 0 AND starts_actual >= 0 AND qualified_actual >= 0
    AND responses_actual >= 0
  ),
  CONSTRAINT ws_weekly_snapshot_uq UNIQUE (tenant_id, recruiter_user_id, week_start)
);

CREATE INDEX IF NOT EXISTS idx_ws_weekly_snapshot_team_week
  ON public.ws_weekly_recruiter_snapshot(tenant_id, team_id, week_start DESC, recruiter_user_id);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='medlivo_team_api_runtime') THEN
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_job_intake_batch TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_job_intake_item TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_customer_job_mapping TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_weekly_recruiter_goal TO medlivo_team_api_runtime';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_weekly_recruiter_snapshot TO medlivo_team_api_runtime';
  END IF;
END
$$;
