from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from .engine import evaluate_hard_gates
from .models import CandidateMatchInput, JobMatchInput


def _tokens(value: str | None) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", (value or "").lower())
        if len(token) > 1
    }


def _candidate_text(candidate: CandidateMatchInput, extra_text: str | None = None) -> str:
    parts = [
        candidate.profession,
        candidate.specialty,
        *candidate.resume_specialties,
        *candidate.care_settings,
        *candidate.clinical_skills,
        candidate.city,
        candidate.state,
        *(license.license_type for license in candidate.licenses),
        *(cert.name for cert in candidate.certifications),
        extra_text,
    ]
    return " ".join(str(part) for part in parts if part)


def _job_text(job: JobMatchInput, extra_text: str | None = None) -> str:
    parts = [
        job.division,
        job.profession,
        job.specialty,
        job.care_setting,
        job.city,
        job.state,
        *job.required_license_states,
        *job.required_certifications,
        extra_text,
    ]
    return " ".join(str(part) for part in parts if part)


def lexical_similarity(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens)
    return overlap / math.sqrt(len(left_tokens) * len(right_tokens))


def cosine_similarity(left: Sequence[float] | None, right: Sequence[float] | None) -> float | None:
    if left is None or right is None or len(left) != len(right) or not left:
        return None
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return None
    return max(-1.0, min(1.0, numerator / (left_norm * right_norm)))


@dataclass(frozen=True)
class RetrievalHit:
    candidate_id: str
    retrieval_score: float
    lexical_score: float
    vector_score: float | None
    reason: str


def retrieve_candidates(
    job: JobMatchInput,
    candidates: Iterable[CandidateMatchInput],
    *,
    job_text: str | None = None,
    candidate_texts: Mapping[str, str] | None = None,
    job_embedding: Sequence[float] | None = None,
    candidate_embeddings: Mapping[str, Sequence[float]] | None = None,
    limit: int = 50,
) -> list[RetrievalHit]:
    """Retrieve an explainable shortlist without bypassing hard gates.

    Hard-gate failures are removed before lexical/vector ranking. Vector similarity
    is optional so the same code path works before a production embedding store
    is enabled.
    """
    if limit <= 0:
        return []

    candidate_texts = candidate_texts or {}
    candidate_embeddings = candidate_embeddings or {}
    source_job_text = _job_text(job, job_text)
    hits: list[RetrievalHit] = []

    for candidate in candidates:
        gates = evaluate_hard_gates(job, candidate)
        if any(not gate.passed for gate in gates):
            continue

        lexical = lexical_similarity(
            source_job_text,
            _candidate_text(candidate, candidate_texts.get(candidate.candidate_id)),
        )
        vector = cosine_similarity(
            job_embedding,
            candidate_embeddings.get(candidate.candidate_id),
        )

        if vector is None:
            score = lexical
            reason = f"Eligible by hard gates; lexical similarity {lexical:.3f}"
        else:
            normalized_vector = (vector + 1.0) / 2.0
            score = (0.4 * lexical) + (0.6 * normalized_vector)
            reason = (
                "Eligible by hard gates; hybrid retrieval "
                f"lexical={lexical:.3f}, vector={normalized_vector:.3f}"
            )

        hits.append(
            RetrievalHit(
                candidate_id=candidate.candidate_id,
                retrieval_score=round(score, 4),
                lexical_score=round(lexical, 4),
                vector_score=round((vector + 1.0) / 2.0, 4) if vector is not None else None,
                reason=reason,
            )
        )

    hits.sort(key=lambda hit: (-hit.retrieval_score, hit.candidate_id))
    return hits[:limit]
