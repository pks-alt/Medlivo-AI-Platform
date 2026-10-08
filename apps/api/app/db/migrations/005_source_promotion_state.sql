ALTER TABLE job_source_record
  ADD COLUMN IF NOT EXISTS promoted_at timestamptz,
  ADD COLUMN IF NOT EXISTS promotion_version text;

ALTER TABLE candidate_source_record
  ADD COLUMN IF NOT EXISTS promoted_at timestamptz,
  ADD COLUMN IF NOT EXISTS promotion_version text;

CREATE INDEX IF NOT EXISTS idx_job_source_record_promotion_pending
  ON job_source_record (tenant_id, source_system, updated_at)
  WHERE promoted_at IS NULL OR promoted_at < updated_at;

CREATE INDEX IF NOT EXISTS idx_candidate_source_record_promotion_pending
  ON candidate_source_record (tenant_id, source_system, updated_at)
  WHERE promoted_at IS NULL OR promoted_at < updated_at;
