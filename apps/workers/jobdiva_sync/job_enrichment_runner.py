from __future__ import annotations

from .job_enrichment import build_job_intelligence
from .job_intelligence_store import JobIntelligenceStore


async def enrich_pending_jobs(
    client,
    store: JobIntelligenceStore,
    *,
    tenant_id: str,
    limit: int = 25,
) -> dict[str, int]:
    """Enrich a bounded batch of canonical jobs from JobDiva JobsDetail."""
    pending = await store.pending_sources(tenant_id=tenant_id, limit=limit)
    enriched = failed = 0

    for item in pending:
        try:
            intelligence, _stats = await build_job_intelligence(
                client,
                source_job_id=item["source_job_id"],
            )
            await store.persist(
                tenant_id=tenant_id,
                source_record_id=item["source_record_id"],
                job_id=item["job_id"],
                intelligence=intelligence,
            )
            enriched += 1
        except Exception as exc:
            failed += 1
            await store.mark_error(
                tenant_id=tenant_id,
                source_record_id=item["source_record_id"],
                error_code=type(exc).__name__,
            )

    return {
        "pending": len(pending),
        "enriched": enriched,
        "failed": failed,
    }
