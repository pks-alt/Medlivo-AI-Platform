from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass

from psycopg import AsyncConnection

from jobdiva_connector.client import JobDivaClient, JobDivaError, JobDivaHTTPError
from jobdiva_connector.config import JobDivaSettings
from jobdiva_sync import (
    CanonicalPromoter,
    CandidateIntelligenceStore,
    JobIntelligenceStore,
    MatchingStore,
    PostgresSyncStore,
    SyncStream,
    activate_matching,
    enrich_pending_candidates,
    enrich_pending_jobs,
    run_delta_sync,
)


@dataclass(frozen=True)
class PilotLimits:
    sync_page_size: int = 100
    promotion_limit: int = 250
    candidate_enrichment_limit: int = 25
    job_enrichment_limit: int = 25
    matching_limit: int = 500
    max_resumes: int = 3


def _bounded_int(name: str, default: int, low: int, high: int) -> int:
    raw = os.getenv(name)
    value = default if raw in (None, "") else int(raw)
    if value < low or value > high:
        raise ValueError(f"{name} must be between {low} and {high}")
    return value


def _psycopg_database_url(database_url: str) -> str:
    """Convert the staging SQLAlchemy psycopg URL into libpq/psycopg form."""
    if database_url.startswith("postgresql+psycopg://"):
        return database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    return database_url


def limits_from_env() -> PilotLimits:
    return PilotLimits(
        sync_page_size=_bounded_int("PILOT_SYNC_PAGE_SIZE", 100, 1, 250),
        promotion_limit=_bounded_int("PILOT_PROMOTION_LIMIT", 250, 1, 1000),
        candidate_enrichment_limit=_bounded_int("PILOT_CANDIDATE_ENRICHMENT_LIMIT", 25, 1, 100),
        job_enrichment_limit=_bounded_int("PILOT_JOB_ENRICHMENT_LIMIT", 25, 1, 100),
        matching_limit=_bounded_int("PILOT_MATCHING_LIMIT", 500, 1, 2000),
        max_resumes=_bounded_int("PILOT_MAX_RESUMES", 3, 1, 5),
    )


def pilot_enabled() -> bool:
    return os.getenv("PILOT_ENABLED", "false").strip().lower() == "true"


def diagnostics_only() -> bool:
    return os.getenv("PILOT_DIAGNOSTICS_ONLY", "false").strip().lower() == "true"


def emit_event(payload: dict) -> None:
    """Emit one sanitized structured event and force it to Cloud Run logs."""
    sys.stderr.write(json.dumps(payload, default=str, sort_keys=True) + "\n")
    sys.stderr.flush()


REQUIRED_SCHEMA = {
    "integration_sync_checkpoint": {"tenant_id", "source_system", "stream", "watermark"},
    "integration_sync_run": {"tenant_id", "source_system", "stream", "mode", "status"},
    "job_source_record": {"tenant_id", "job_id", "source_system", "source_id", "enriched_at"},
    "candidate_source_record": {"tenant_id", "candidate_id", "source_system", "source_id", "enriched_at"},
    "job": {"tenant_id", "title", "profession", "status", "owner_user_id"},
    "candidate": {"tenant_id", "canonical_name", "profession", "state", "lifecycle_status"},
    "match": {"tenant_id", "job_id", "candidate_id", "overall_score"},
}


async def check_schema_readiness(connection) -> dict:
    async with connection.cursor() as cur:
        await cur.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            """
        )
        rows = await cur.fetchall()

    present: dict[str, set[str]] = {}
    for table_name, column_name in rows:
        present.setdefault(table_name, set()).add(column_name)

    missing_tables = sorted(table for table in REQUIRED_SCHEMA if table not in present)
    missing_columns = {
        table: sorted(columns - present.get(table, set()))
        for table, columns in REQUIRED_SCHEMA.items()
        if table in present and columns - present.get(table, set())
    }
    return {
        "status": "ready" if not missing_tables and not missing_columns else "not_ready",
        "missing_tables": missing_tables,
        "missing_columns": missing_columns,
    }


async def run_connectivity_diagnostic(client) -> dict:
    result = {
        "authentication": "ok",
        "data_endpoint": "unknown",
        "http_status": None,
        "response_parse": "not_attempted",
    }
    try:
        response = await client.request("GET", client.OPEN_JOBS_PATH)
    except JobDivaHTTPError as exc:
        result["data_endpoint"] = "unauthorized" if exc.status_code in {401, 403} else "http_error"
        result["http_status"] = exc.status_code
        return result
    except JobDivaError:
        result["data_endpoint"] = "connector_error"
        return result

    result["data_endpoint"] = "ok"
    result["http_status"] = response.status_code
    try:
        client._json_records(response)
    except JobDivaError:
        result["response_parse"] = "unexpected_payload"
    else:
        result["response_parse"] = "ok"
    return result


async def run_pilot_once(
    *,
    connection,
    client,
    tenant_id: str,
    limits: PilotLimits,
) -> dict:
    sync_store = PostgresSyncStore(connection)
    promoter = CanonicalPromoter(connection)
    candidate_store = CandidateIntelligenceStore(connection)
    job_store = JobIntelligenceStore(connection)
    matching_store = MatchingStore(connection)

    job_sync = await run_delta_sync(
        client,
        sync_store,
        tenant_id=tenant_id,
        stream=SyncStream.JOBS,
        page_size=limits.sync_page_size,
    )
    candidate_sync = await run_delta_sync(
        client,
        sync_store,
        tenant_id=tenant_id,
        stream=SyncStream.CANDIDATES,
        page_size=limits.sync_page_size,
    )

    job_promotion = await promoter.promote_unlinked(
        tenant_id=tenant_id,
        stream=SyncStream.JOBS,
        limit=limits.promotion_limit,
    )
    candidate_promotion = await promoter.promote_unlinked(
        tenant_id=tenant_id,
        stream=SyncStream.CANDIDATES,
        limit=limits.promotion_limit,
    )

    job_enrichment = await enrich_pending_jobs(
        client,
        job_store,
        tenant_id=tenant_id,
        limit=limits.job_enrichment_limit,
    )
    candidate_enrichment = await enrich_pending_candidates(
        client,
        candidate_store,
        tenant_id=tenant_id,
        limit=limits.candidate_enrichment_limit,
        max_resumes=limits.max_resumes,
    )
    matching = await activate_matching(
        matching_store,
        tenant_id=tenant_id,
        limit=limits.matching_limit,
    )

    return {
        "job_sync": {
            "records_seen": job_sync.records_seen,
            "records_upserted": job_sync.records_upserted,
            "pages_processed": job_sync.pages_processed,
        },
        "candidate_sync": {
            "records_seen": candidate_sync.records_seen,
            "records_upserted": candidate_sync.records_upserted,
            "pages_processed": candidate_sync.pages_processed,
        },
        "job_promotion": job_promotion,
        "candidate_promotion": candidate_promotion,
        "job_enrichment": job_enrichment,
        "candidate_enrichment": candidate_enrichment,
        "matching": matching,
    }


async def main() -> int:
    if not pilot_enabled():
        print("Pilot disabled; no JobDiva reads or database mutations were attempted.")
        return 0

    tenant_id = os.getenv("PILOT_TENANT_ID", "").strip()
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not tenant_id:
        raise RuntimeError("PILOT_TENANT_ID is required when PILOT_ENABLED=true")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required when PILOT_ENABLED=true")

    settings = JobDivaSettings()
    if not settings.live_enabled:
        raise RuntimeError("JOBDIVA_LIVE_ENABLED must be true for an enabled pilot")

    limits = limits_from_env()
    connection = await AsyncConnection.connect(_psycopg_database_url(database_url))
    try:
        schema = await check_schema_readiness(connection)
        if schema["status"] != "ready":
            emit_event({"pilot": "preflight_failed", "stage": "database_schema", **schema})
            return 2

        async with JobDivaClient(settings) as client:
            await client.authenticate()
            if diagnostics_only():
                diagnostic = await run_connectivity_diagnostic(client)
                emit_event({
                    "pilot": "diagnostic",
                    "tenant_id": tenant_id,
                    "database_schema": "ready",
                    "jobdiva": diagnostic,
                })
                return 0 if diagnostic["data_endpoint"] == "ok" else 3

            result = await run_pilot_once(
                connection=connection,
                client=client,
                tenant_id=tenant_id,
                limits=limits,
            )
        emit_event({
            "pilot": "completed",
            "tenant_id": tenant_id,
            "limits": limits.__dict__,
            "result": result,
        })
        return 0
    finally:
        await connection.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
