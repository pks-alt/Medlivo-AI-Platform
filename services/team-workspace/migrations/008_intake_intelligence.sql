-- Wire direct-customer intake to canonical Job Intelligence review output.
-- Apply after 007_enterprise_operations.sql.

ALTER TABLE public.ws_job_intake_item
  ADD COLUMN IF NOT EXISTS standardized_internal_jd jsonb NOT NULL DEFAULT '{}'::jsonb;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='medlivo_team_api_runtime') THEN
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON public.ws_job_intake_item TO medlivo_team_api_runtime';
  END IF;
END
$$;
