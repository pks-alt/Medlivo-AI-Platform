from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from candidate_intelligence import JobDivaCandidateBundle, normalize_candidate


class CandidateDetailClient(Protocol):
    async def candidate_profile(self, candidate_id: str | int) -> list[dict[str, Any]]: ...
    async def candidate_licenses(self, candidate_id: str | int) -> list[dict[str, Any]]: ...
    async def candidate_certifications(self, candidate_id: str | int) -> list[dict[str, Any]]: ...
    async def candidate_resumes(self, candidate_id: str | int) -> list[dict[str, Any]]: ...
    async def resume_text(self, resume_id: str | int) -> list[dict[str, Any]]: ...


@dataclass(frozen=True)
class EnrichmentBundleResult:
    source_candidate_id: str
    profile_records: int
    license_records: int
    certification_records: int
    resume_records: int
    resume_text_records: int


def _resume_id(record: dict[str, Any]) -> str | None:
    for key in ("RESUMEID", "resumeId", "id", "ID"):
        value = record.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (str, int)) and str(value).strip():
            return str(value).strip()
    return None


async def fetch_candidate_bundle(
    client: CandidateDetailClient,
    *,
    source_candidate_id: str,
    source_updated_at: datetime | None = None,
    max_resumes: int = 5,
) -> tuple[JobDivaCandidateBundle, EnrichmentBundleResult]:
    if not source_candidate_id or not str(source_candidate_id).strip():
        raise ValueError("source_candidate_id is required")
    if max_resumes < 1 or max_resumes > 20:
        raise ValueError("max_resumes must be between 1 and 20")

    candidate_id = str(source_candidate_id).strip()
    profile = await client.candidate_profile(candidate_id)
    licenses = await client.candidate_licenses(candidate_id)
    certifications = await client.candidate_certifications(candidate_id)
    resumes = await client.candidate_resumes(candidate_id)

    # Fetch only a bounded number of resume texts. JobDiva remains the source of
    # truth for the resume file itself; Medlivo stores text intelligence only.
    resume_text_records: dict[str, list[dict[str, Any]]] = {}
    for record in resumes[:max_resumes]:
        resume_id = _resume_id(record)
        if resume_id:
            resume_text_records[resume_id] = await client.resume_text(resume_id)

    bundle = JobDivaCandidateBundle(
        candidate_id=candidate_id,
        source_updated_at=source_updated_at,
        profile_records=profile,
        license_records=licenses,
        certification_records=certifications,
        resume_records=resumes,
        resume_text_records=resume_text_records,
    )
    return bundle, EnrichmentBundleResult(
        source_candidate_id=candidate_id,
        profile_records=len(profile),
        license_records=len(licenses),
        certification_records=len(certifications),
        resume_records=len(resumes),
        resume_text_records=sum(len(v) for v in resume_text_records.values()),
    )


async def build_candidate_intelligence(
    client: CandidateDetailClient,
    *,
    source_candidate_id: str,
    source_updated_at: datetime | None = None,
    max_resumes: int = 5,
):
    bundle, stats = await fetch_candidate_bundle(
        client,
        source_candidate_id=source_candidate_id,
        source_updated_at=source_updated_at,
        max_resumes=max_resumes,
    )
    return normalize_candidate(bundle), stats
