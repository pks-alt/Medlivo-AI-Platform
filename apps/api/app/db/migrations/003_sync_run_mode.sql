ALTER TABLE integration_sync_run
  ADD COLUMN IF NOT EXISTS mode text NOT NULL DEFAULT 'delta';

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'integration_sync_run_mode_check'
  ) THEN
    ALTER TABLE integration_sync_run
      ADD CONSTRAINT integration_sync_run_mode_check
      CHECK (mode IN ('delta','backfill'));
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_integration_sync_run_mode_window
  ON integration_sync_run (
    tenant_id,
    source_system,
    stream,
    mode,
    window_start,
    window_end
  );
