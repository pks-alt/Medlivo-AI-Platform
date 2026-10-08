from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from psycopg import AsyncConnection

from jobdiva_connector.client import JobDivaClient
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
        async with JobDivaClient(settings) as client:
            result = await run_pilot_once(
                connection=connection,
                client=client,
                tenant_id=tenant_id,
                limits=limits,
            )
        print({
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
