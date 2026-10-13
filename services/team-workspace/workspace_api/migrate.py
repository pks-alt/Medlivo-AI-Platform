"""Run one reviewed SQL migration against the configured workspace database.

The runner records reviewed migrations by filename + SHA-256 checksum so deploys
do not blindly replay already-applied DDL. For migrations 014-021, an existing
sentinel object can be baselined once when introducing the ledger to an older
staging database.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import sys
from sqlalchemy import create_engine, text


ALLOWED_PREFIX = Path("/app/migrations")

# Existing rollout objects used only to bootstrap the migration ledger safely.
# A sentinel means that migration's principal schema object already exists.
SENTINELS = {
    "014_job_content_standards.sql": ("table", "ws_job_content_standard"),
    "015_recruiter_execution_controls.sql": ("table", "ws_candidate_engagement_event"),
    "016_outreach_drafts.sql": ("table", "ws_outreach_draft"),
    "017_outreach_execution.sql": ("table", "ws_outreach_execution"),
    "018_gmail_provider_pilot.sql": ("table", "ws_gmail_connection"),
    "019_gmail_reply_sync.sql": ("table", "ws_gmail_message"),
    "020_followup_sequences.sql": ("table", "ws_followup_sequence_step"),
    "021_scheduled_followup_execution.sql": ("column", "ws_outreach_draft", "followup_sequence_step_id"),
}


def _ensure_ledger(conn):
    conn.exec_driver_sql("""
        CREATE TABLE IF NOT EXISTS public.ws_schema_migration (
          migration_name text PRIMARY KEY,
          checksum_sha256 text NOT NULL,
          disposition text NOT NULL,
          applied_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT ws_schema_migration_disposition_ck
            CHECK (disposition IN ('applied','baselined'))
        )
    """)


def _sentinel_exists(conn, migration_name: str) -> bool:
    sentinel = SENTINELS.get(migration_name)
    if sentinel is None:
        return False
    if sentinel[0] == "table":
        return conn.execute(
            text("SELECT to_regclass(:name) IS NOT NULL"),
            {"name": "public." + sentinel[1]},
        ).scalar_one()
    if sentinel[0] == "column":
        return conn.execute(text("""
            SELECT EXISTS (
              SELECT 1
              FROM information_schema.columns
              WHERE table_schema='public'
                AND table_name=:table_name
                AND column_name=:column_name
            )
        """), {"table_name": sentinel[1], "column_name": sentinel[2]}).scalar_one()
    return False


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        raise SystemExit("usage: python -m workspace_api.migrate /app/migrations/<reviewed.sql>")
    path = Path(argv[0]).resolve()
    if path.parent != ALLOWED_PREFIX or path.suffix != ".sql":
        raise SystemExit("migration path is not allowed")
    database_url = os.environ.get("WORKSPACE_DATABASE_URL")
    if not database_url:
        raise SystemExit("WORKSPACE_DATABASE_URL is required")

    sql = path.read_text(encoding="utf-8")
    checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
    engine = create_engine(database_url, pool_pre_ping=True, hide_parameters=True)
    try:
        with engine.begin() as conn:
            _ensure_ledger(conn)
            existing = conn.execute(text("""
                SELECT checksum_sha256, disposition
                FROM public.ws_schema_migration
                WHERE migration_name=:migration_name
            """), {"migration_name": path.name}).mappings().first()
            if existing is not None:
                if existing["checksum_sha256"] != checksum:
                    raise SystemExit(
                        f"Reviewed migration checksum changed after recording: {path.name}"
                    )
                print(f"Migration already recorded ({existing['disposition']}): {path.name}")
                return

            if _sentinel_exists(conn, path.name):
                conn.execute(text("""
                    INSERT INTO public.ws_schema_migration
                      (migration_name, checksum_sha256, disposition)
                    VALUES (:migration_name, :checksum, 'baselined')
                """), {"migration_name": path.name, "checksum": checksum})
                print(f"Baselined existing reviewed migration: {path.name}")
                return

            conn.exec_driver_sql(sql)
            conn.execute(text("""
                INSERT INTO public.ws_schema_migration
                  (migration_name, checksum_sha256, disposition)
                VALUES (:migration_name, :checksum, 'applied')
            """), {"migration_name": path.name, "checksum": checksum})
    finally:
        engine.dispose()
    print(f"Applied reviewed migration: {path.name}")


if __name__ == "__main__":
    main()
