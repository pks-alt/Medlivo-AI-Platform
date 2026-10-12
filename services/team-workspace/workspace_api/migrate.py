"""Run one reviewed SQL migration against the configured workspace database.

This module is intended for controlled staging/production deployment jobs.
It never discovers migrations automatically and never logs database URLs.
"""
from __future__ import annotations
import os
from pathlib import Path
import sys
from sqlalchemy import create_engine


ALLOWED_PREFIX = Path("/app/migrations")


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
    engine = create_engine(database_url, pool_pre_ping=True, hide_parameters=True)
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(sql)
    finally:
        engine.dispose()
    print(f"Applied reviewed migration: {path.name}")


if __name__ == "__main__":
    main()
