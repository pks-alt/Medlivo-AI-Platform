ALTER TABLE candidate_source_record
  ADD COLUMN IF NOT EXISTS enriched_at timestamptz,
  ADD COLUMN IF NOT EXISTS enrichment_version text,
  ADD COLUMN IF NOT EXISTS enrichment_error_code text;

ALTER TABLE resume_version
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE candidate_license
  ADD COLUMN IF NOT EXISTS source_system text,
  ADD COLUMN IF NOT EXISTS source_reference text,
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE candidate_certification
  ADD COLUMN IF NOT EXISTS source_system text,
  ADD COLUMN IF NOT EXISTS source_reference text,
  ADD COLUMN IF NOT EXISTS raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE candidate_evidence
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_candidate_source_enrichment_pending
  ON candidate_source_record (tenant_id, source_system, updated_at)
  WHERE candidate_id IS NOT NULL
    AND (enriched_at IS NULL OR enriched_at < updated_at);

CREATE UNIQUE INDEX IF NOT EXISTS uq_resume_version_source
  ON resume_version (tenant_id, candidate_id, source_resume_id)
  WHERE source_resume_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_candidate_license_source
  ON candidate_license (tenant_id, candidate_id, source_system, source_reference)
  WHERE source_system IS NOT NULL AND source_reference IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_candidate_certification_source
  ON candidate_certification (tenant_id, candidate_id, source_system, source_reference)
  WHERE source_system IS NOT NULL AND source_reference IS NOT NULL;
