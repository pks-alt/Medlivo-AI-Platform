from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from calendar import monthrange
from datetime import datetime, timedelta, timezone

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
    backfill_windows,
    run_backfill_window,
    persist_active_job_sample,
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


def active_jobs_by_division_mode() -> bool:
    return os.getenv("PILOT_ACTIVE_JOBS_BY_DIVISION", "false").strip().lower() == "true"


def six_month_jobs_mode() -> bool:
    return os.getenv("PILOT_SIX_MONTH_JOBS", "false").strip().lower() == "true"


def six_calendar_months_ago(value: datetime) -> datetime:
    month = value.month - 6
    year = value.year
    if month <= 0:
        month += 12
        year -= 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


async def import_six_month_jobs(connection, client, *, tenant_id: str, page_size: int = 100) -> dict:
    end = datetime.now(timezone.utc)
    start = six_calendar_months_ago(end)
    source_ids: set[str] = set()
    sync_store = PostgresSyncStore(connection)
    promoter = CanonicalPromoter(connection)

    runs = []
    for window_start, window_end in backfill_windows(start, end):
        runs.append(await run_backfill_window(
            client,
            sync_store,
            tenant_id=tenant_id,
            stream=SyncStream.JOBS,
            window_start=window_start,
            window_end=window_end,
            page_size=page_size,
            source_ids_sink=source_ids,
        ))

    if not source_ids:
        return {
            "window_start": start.isoformat(),
            "window_end": end.isoformat(),
            "windows_completed": len(runs),
            "source_jobs": 0,
            "promotion": {"promoted": 0, "skipped": 0, "failed": 0},
            "status_counts": {},
            "division_counts": {},
            "includes_closed": True,
            "historical_scope": "last_six_calendar_months",
        }

    promotion = await promoter.promote_unlinked(
        tenant_id=tenant_id,
        stream=SyncStream.JOBS,
        limit=len(source_ids),
        source_ids=sorted(source_ids),
    )

    async with connection.cursor() as cur:
        await cur.execute(
            """
            SELECT status, count(*)
            FROM job
            WHERE tenant_id=%s
              AND id IN (
                SELECT job_id FROM job_source_record
                WHERE tenant_id=%s AND source_system='jobdiva'
                  AND source_id = ANY(%s)
              )
            GROUP BY status
            ORDER BY status
            """,
            (tenant_id, tenant_id, sorted(source_ids)),
        )
        status_rows = await cur.fetchall()
        await cur.execute(
            """
            SELECT COALESCE(division,'Unclassified'), count(*)
            FROM job
            WHERE tenant_id=%s
              AND id IN (
                SELECT job_id FROM job_source_record
                WHERE tenant_id=%s AND source_system='jobdiva'
                  AND source_id = ANY(%s)
              )
            GROUP BY COALESCE(division,'Unclassified')
            ORDER BY 1
            """,
            (tenant_id, tenant_id, sorted(source_ids)),
        )
        division_rows = await cur.fetchall()

    return {
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "windows_completed": len(runs),
        "source_jobs": len(source_ids),
        "promotion": promotion,
        "status_counts": {str(k): int(v) for k, v in status_rows},
        "division_counts": {str(k): int(v) for k, v in division_rows},
        "includes_closed": True,
        "historical_scope": "last_six_calendar_months",
    }


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


def _first_source_id(records: list[dict], keys: tuple[str, ...]) -> str | None:
    for record in records:
        for key in keys:
            value = record.get(key)
            if isinstance(value, bool):
                continue
            if isinstance(value, (str, int)) and str(value).strip():
                return str(value).strip()
    return None


async def _diagnostic_read(name: str, call) -> tuple[dict, list[dict]]:
    try:
        records = await call()
    except JobDivaHTTPError as exc:
        return {
            "status": "unauthorized" if exc.status_code in {401, 403} else "http_error",
            "http_status": exc.status_code,
            "records": None,
        }, []
    except JobDivaError:
        return {"status": "connector_error", "http_status": None, "records": None}, []
    return {"status": "ok", "http_status": 200, "records": len(records)}, records


async def run_full_read_diagnostic(client, *, now: datetime | None = None) -> dict:
    """Verify the enabled Phase 1 JobDiva read contract without persisting payload data."""
    current = now or datetime.now()
    start = current - timedelta(days=14)
    endpoints: dict[str, dict] = {}

    endpoints["open_jobs"], open_jobs = await _diagnostic_read("open_jobs", client.open_jobs)
    open_jobs_shape = None
    if endpoints["open_jobs"]["status"] == "connector_error":
        try:
            open_jobs_shape = await client.open_jobs_response_shape()
        except JobDivaHTTPError as exc:
            open_jobs_shape = {"probe_status": "http_error", "http_status": exc.status_code}
        except JobDivaError:
            open_jobs_shape = {"probe_status": "connector_error"}

    endpoints["updated_jobs"], updated_jobs = await _diagnostic_read(
        "updated_jobs",
        lambda: client.updated_jobs(
            from_date=start, to_date=current, page_number=1, page_size=5
        ),
    )
    endpoints["updated_candidates"], updated_candidates = await _diagnostic_read(
        "updated_candidates",
        lambda: client.updated_candidates(
            from_date=start, to_date=current, page_number=1, page_size=5
        ),
    )

    job_id = _first_source_id(
        open_jobs + updated_jobs, ("JOBID", "jobId", "jobID", "id", "ID")
    )
    if job_id:
        endpoints["job_detail"], _ = await _diagnostic_read(
            "job_detail", lambda: client.job_detail(job_id)
        )
    else:
        endpoints["job_detail"] = {
            "status": "not_tested_no_sample", "http_status": None, "records": None
        }

    candidate_id = _first_source_id(
        updated_candidates,
        ("CANDIDATEID", "candidateId", "candidateID", "id", "ID"),
    )
    if candidate_id:
        endpoints["candidate_profile"], _ = await _diagnostic_read(
            "candidate_profile", lambda: client.candidate_profile(candidate_id)
        )
        endpoints["candidate_licenses"], _ = await _diagnostic_read(
            "candidate_licenses", lambda: client.candidate_licenses(candidate_id)
        )
        endpoints["candidate_certifications"], _ = await _diagnostic_read(
            "candidate_certifications", lambda: client.candidate_certifications(candidate_id)
        )
        endpoints["candidate_resumes"], resumes = await _diagnostic_read(
            "candidate_resumes", lambda: client.candidate_resumes(candidate_id)
        )
        resume_id = _first_source_id(
            resumes, ("RESUMEID", "resumeId", "resumeID", "id", "ID")
        )
        if resume_id:
            endpoints["resume_text"], _ = await _diagnostic_read(
                "resume_text", lambda: client.resume_text(resume_id)
            )
        else:
            endpoints["resume_text"] = {
                "status": "not_tested_no_sample", "http_status": None, "records": None
            }
    else:
        for name in (
            "candidate_profile",
            "candidate_licenses",
            "candidate_certifications",
            "candidate_resumes",
            "resume_text",
        ):
            endpoints[name] = {
                "status": "not_tested_no_sample", "http_status": None, "records": None
            }

    statuses = [item["status"] for item in endpoints.values()]
    if any(status in {"unauthorized", "http_error", "connector_error"} for status in statuses):
        contract_status = "failed"
    elif any(status == "not_tested_no_sample" for status in statuses):
        contract_status = "partial"
    else:
        contract_status = "verified"

    return {
        "authentication": "ok",
        "contract_status": contract_status,
        "window_days": 14,
        "page_size": 5,
        "open_jobs_shape": open_jobs_shape,
        "endpoints": endpoints,
    }


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
                diagnostic = await run_full_read_diagnostic(client)
                emit_event({
                    "pilot": "diagnostic",
                    "tenant_id": tenant_id,
                    "database_schema": "ready",
                    "jobdiva": diagnostic,
                })
                return 0 if diagnostic["contract_status"] == "verified" else 3

            if six_month_jobs_mode():
                result = await import_six_month_jobs(
                    connection,
                    client,
                    tenant_id=tenant_id,
                    page_size=limits.sync_page_size,
                )
                emit_event({
                    "pilot": "six_month_jobs",
                    "tenant_id": tenant_id,
                    "result": result,
                })
                return 0

            if active_jobs_by_division_mode():
                per_division = _bounded_int("PILOT_ACTIVE_JOBS_PER_DIVISION", 100, 1, 500)
                max_scan = _bounded_int("PILOT_ACTIVE_JOBS_MAX_SCAN", 5000, per_division, 20000)
                result = await persist_active_job_sample(
                    client,
                    PostgresSyncStore(connection),
                    CanonicalPromoter(connection),
                    tenant_id=tenant_id,
                    per_division=per_division,
                    max_scan=max_scan,
                )
                emit_event({
                    "pilot": "active_jobs_by_division",
                    "tenant_id": tenant_id,
                    "result": result,
                })
                return 0 if result["complete"] else 4

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
