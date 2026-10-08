from __future__ import annotations

from matching_engine import score_match

from .matching_adapter import candidate_match_input, job_match_input
from .matching_store import MatchingStore


async def activate_matching(
    store: MatchingStore,
    *,
    tenant_id: str,
    limit: int = 500,
) -> dict[str, int]:
    """Evaluate stale/new canonical job-candidate pairs and persist results."""
    pairs = await store.pending_pairs(tenant_id=tenant_id, limit=limit)
    evaluated = eligible = excluded = failed = 0

    job_cache: dict[str, tuple[dict, list[dict]]] = {}
    candidate_cache: dict[str, tuple[dict, list[dict], list[dict], dict | None, bool]] = {}

    for pair in pairs:
        job_id = str(pair["job_id"])
        candidate_id = str(pair["candidate_id"])
        try:
            if job_id not in job_cache:
                job_cache[job_id] = await store.load_job(
                    tenant_id=tenant_id,
                    job_id=job_id,
                )
            if candidate_id not in candidate_cache:
                candidate_cache[candidate_id] = await store.load_candidate(
                    tenant_id=tenant_id,
                    candidate_id=candidate_id,
                )

            job, requirements = job_cache[job_id]
            candidate, licenses, certifications, availability, resume_available = candidate_cache[candidate_id]

            job_input = job_match_input(job, requirements=requirements)
            candidate_input = candidate_match_input(
                candidate,
                licenses=licenses,
                certifications=certifications,
                availability=availability,
                resume_available=resume_available,
            )
            result = score_match(job_input, candidate_input)
            await store.persist_result(
                tenant_id=tenant_id,
                result=result,
            )
            evaluated += 1
            if result.eligible:
                eligible += 1
            else:
                excluded += 1
        except Exception:
            # One malformed pair must not block evaluation of the remaining
            # bounded batch. Operational metrics surface the failure count.
            failed += 1

    return {
        "pending": len(pairs),
        "evaluated": evaluated,
        "eligible": eligible,
        "excluded": excluded,
        "failed": failed,
    }
