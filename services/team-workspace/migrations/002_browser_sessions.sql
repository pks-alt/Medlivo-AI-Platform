-- Run in the staging session database using a migration-only owner, never startup.
-- No data, identity binding, roles or secrets are seeded by this migration.
CREATE TABLE IF NOT EXISTS wb_login (
  id_hash char(64) PRIMARY KEY,
  state_hash char(64) NOT NULL,
  ciphertext text NOT NULL,
  created_at bigint NOT NULL,
  expires_at bigint NOT NULL,
  CHECK (expires_at > created_at)
);
CREATE INDEX IF NOT EXISTS wb_login_expiry ON wb_login(expires_at);
CREATE INDEX IF NOT EXISTS wb_login_created ON wb_login(created_at);
CREATE TABLE IF NOT EXISTS wb_session (
  id_hash char(64) PRIMARY KEY,
  ciphertext text NOT NULL,
  expires_at bigint NOT NULL,
  idle_expires_at bigint NOT NULL,
  CHECK (idle_expires_at <= expires_at)
);
CREATE INDEX IF NOT EXISTS wb_session_expiry ON wb_session(expires_at);
-- Grant only SELECT, INSERT, UPDATE, DELETE on these two tables to the dedicated
-- browser gateway's non-owner DB role. Grant it NO identity or recruiter-table access.
-- Cleanup at login is implemented; add periodic expired-row cleanup operationally.
