from __future__ import annotations

from collections import defaultdict

from matching_engine import evaluate_hard_gates, retrieve_candidates, score_match

from .matching_adapter import candidate_match_input, job_match_input
from .matching_store import MatchingStore


async def activate_matching(
    store: MatchingStore,
    *,
    tenant_id: str,
    limit: int = 500,
) -> dict[str, int]:
    """Evaluate stale/new canonical job-candidate pairs and persist results.

    Hard-gate failures are persisted first for auditability. Eligible candidates
    are then ordered by hybrid retrieval before deterministic scoring. Retrieval
    changes processing priority only; it does not replace hard gates or the
    authoritative 0-10 score.
    """
    pairs = await store.pending_pairs(tenant_id=tenant_id, limit=limit)
    evaluated = eligible = excluded = failed = 0

    job_cache: dict[str, tuple[dict, list[dict]]] = {}
    candidate_cache: dict[str, tuple[dict, list[dict], list[dict], dict | None, bool]] = {}
    pair_groups: dict[str, list[str]] = defaultdict(list)

    for pair in pairs:
        pair_groups[str(pair["job_id"])].append(str(pair["candidate_id"]))

    for job_id, candidate_ids in pair_groups.items():
        try:
            if job_id not in job_cache:
                job_cache[job_id] = await store.load_job(
                    tenant_id=tenant_id,
                    job_id=job_id,
                )
            job, requirements = job_cache[job_id]
            job_input = job_match_input(job, requirements=requirements)
        except Exception:
            failed += len(candidate_ids)
            continue

        eligible_inputs = []
        by_candidate_id = {}

        for candidate_id in candidate_ids:
            try:
                if candidate_id not in candidate_cache:
                    candidate_cache[candidate_id] = await store.load_candidate(
                        tenant_id=tenant_id,
                        candidate_id=candidate_id,
                    )

                candidate, licenses, certifications, availability, resume_available = candidate_cache[candidate_id]
                candidate_input = candidate_match_input(
                    candidate,
                    licenses=licenses,
                    certifications=certifications,
                    availability=availability,
                    resume_available=resume_available,
                )
                by_candidate_id[candidate_id] = candidate_input

                gates = evaluate_hard_gates(job_input, candidate_input)
                if any(not gate.passed for gate in gates):
                    result = score_match(job_input, candidate_input)
                    await store.persist_result(tenant_id=tenant_id, result=result)
                    evaluated += 1
                    excluded += 1
                    continue

                eligible_inputs.append(candidate_input)
            except Exception:
                failed += 1

        if not eligible_inputs:
            continue

        try:
            ranked = retrieve_candidates(
                job_input,
                eligible_inputs,
                limit=len(eligible_inputs),
            )
            ranked_ids = [hit.candidate_id for hit in ranked]
        except Exception:
            # Retrieval must never block deterministic matching. Fall back to
            # stable input order if retrieval is unavailable or malformed.
            ranked_ids = [item.candidate_id for item in eligible_inputs]

        for candidate_id in ranked_ids:
            try:
                result = score_match(job_input, by_candidate_id[candidate_id])
                await store.persist_result(tenant_id=tenant_id, result=result)
                evaluated += 1
                eligible += 1
            except Exception:
                failed += 1

    return {
        "pending": len(pairs),
        "evaluated": evaluated,
        "eligible": eligible,
        "excluded": excluded,
        "failed": failed,
    }
