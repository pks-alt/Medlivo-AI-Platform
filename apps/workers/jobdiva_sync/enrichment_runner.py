from __future__ import annotations

from .enrichment import build_candidate_intelligence
from .intelligence_store import CandidateIntelligenceStore


async def enrich_pending_candidates(
    client,
    store: CandidateIntelligenceStore,
    *,
    tenant_id: str,
    limit: int = 25,
    max_resumes: int = 5,
) -> dict[str, int]:
    """Enrich a bounded batch of canonical candidates from JobDiva details."""
    pending = await store.pending_sources(tenant_id=tenant_id, limit=limit)
    enriched = failed = 0

    for item in pending:
        try:
            intelligence, _stats = await build_candidate_intelligence(
                client,
                source_candidate_id=item["source_candidate_id"],
                source_updated_at=item["source_updated_at"],
                max_resumes=max_resumes,
            )
            await store.persist(
                tenant_id=tenant_id,
                source_record_id=item["source_record_id"],
                candidate_id=item["candidate_id"],
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
