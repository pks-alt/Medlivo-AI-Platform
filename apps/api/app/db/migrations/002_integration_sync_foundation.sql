CREATE TABLE IF NOT EXISTS integration_sync_checkpoint (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  source_system text NOT NULL,
  stream text NOT NULL,
  watermark timestamptz,
  last_success_at timestamptz,
  last_run_id uuid,
  last_error_code text,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, source_system, stream)
);

CREATE TABLE IF NOT EXISTS integration_sync_run (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenant(id),
  source_system text NOT NULL,
  stream text NOT NULL,
  mode text NOT NULL DEFAULT 'delta' CHECK (mode IN ('delta','backfill')),
  status text NOT NULL CHECK (status IN ('running','succeeded','failed')),
  window_start timestamptz NOT NULL,
  window_end timestamptz NOT NULL,
  pages_processed integer NOT NULL DEFAULT 0,
  records_seen integer NOT NULL DEFAULT 0,
  records_upserted integer NOT NULL DEFAULT 0,
  error_code text,
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_integration_sync_run_stream_started
  ON integration_sync_run (tenant_id, source_system, stream, started_at DESC);
