ALTER TABLE job_source_record
  ADD COLUMN IF NOT EXISTS enriched_at timestamptz,
  ADD COLUMN IF NOT EXISTS enrichment_version text,
  ADD COLUMN IF NOT EXISTS enrichment_error_code text;

CREATE INDEX IF NOT EXISTS idx_job_source_enrichment_pending
  ON job_source_record (tenant_id, source_system, updated_at)
  WHERE job_id IS NOT NULL
    AND (enriched_at IS NULL OR enriched_at < updated_at);
