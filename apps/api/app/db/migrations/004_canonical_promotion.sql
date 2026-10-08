CREATE TABLE IF NOT EXISTS integration_promotion_run (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  source_system text NOT NULL,
  entity_type text NOT NULL CHECK (entity_type IN ('job','candidate')),
  status text NOT NULL CHECK (status IN ('running','succeeded','failed')),
  source_records_seen integer NOT NULL DEFAULT 0,
  promoted integer NOT NULL DEFAULT 0,
  skipped integer NOT NULL DEFAULT 0,
  failed integer NOT NULL DEFAULT 0,
  error_code text,
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_integration_promotion_run_started
  ON integration_promotion_run (tenant_id, source_system, entity_type, started_at DESC);
