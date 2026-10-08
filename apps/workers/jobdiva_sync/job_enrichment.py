from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Protocol

from job_intelligence import JobRequirement, normalize_job


class JobDetailClient(Protocol):
    async def job_detail(self, job_id: str | int) -> list[dict[str, Any]]: ...


@dataclass(frozen=True)
class JobEnrichmentResult:
    source_job_id: str
    detail_records: int
    requirements: int


def _first(payload: dict[str, Any], names: Iterable[str]):
    for name in names:
        value = payload.get(name)
        if value not in (None, ""):
            return value
    return None


def _values(value) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, (list, tuple, set)):
        raw = list(value)
    else:
        text = str(value).strip()
        if not text:
            return []
        raw = [part.strip() for part in text.replace(";", ",").split(",")]
    result: list[str] = []
    for item in raw:
        text = str(item).strip()
        if text and text not in result:
            result.append(text)
    return result


def explicit_requirements(payload: dict[str, Any]) -> list[JobRequirement]:
    """Extract hard gates only from explicit requirement fields.

    Free-text descriptions are deliberately excluded from hard-gate creation.
    """
    result: list[JobRequirement] = []

    license_value = _first(payload, (
        "REQUIREDLICENSESTATE", "requiredLicenseState",
        "REQUIREDLICENSESTATES", "requiredLicenseStates",
        "LICENSESTATE", "licenseState",
    ))
    for state in _values(license_value):
        normalized = state.upper()
        if len(normalized) == 2:
            result.append(JobRequirement(
                kind="license",
                value=normalized,
                required=True,
                source_field="required_license_state",
            ))

    cert_value = _first(payload, (
        "REQUIREDCERTIFICATION", "requiredCertification",
        "REQUIREDCERTIFICATIONS", "requiredCertifications",
        "CERTIFICATION", "certification",
        "CERTIFICATIONS", "certifications",
    ))
    for cert in _values(cert_value):
        result.append(JobRequirement(
            kind="certification",
            value=cert,
            required=True,
            source_field="required_certification",
        ))

    setting = _first(payload, ("CARESETTING", "careSetting", "SETTING", "setting"))
    if setting not in (None, ""):
        result.append(JobRequirement(
            kind="setting",
            value=str(setting).strip(),
            required=True,
            source_field="care_setting",
        ))

    return result


async def build_job_intelligence(
    client: JobDetailClient,
    *,
    source_job_id: str,
):
    if not source_job_id or not str(source_job_id).strip():
        raise ValueError("source_job_id is required")

    job_id = str(source_job_id).strip()
    records = await client.job_detail(job_id)
    if not records:
        raise ValueError("JobDiva JobsDetail returned no records")

    # If JobDiva ever returns multiple rows, only a row explicitly matching the
    # requested ID may be used. Otherwise refuse to guess.
    chosen = None
    for record in records:
        candidate_id = _first(record, ("JOBID", "jobId", "jobID", "id", "ID"))
        if candidate_id is not None and str(candidate_id).strip() == job_id:
            chosen = record
            break
    if chosen is None:
        if len(records) == 1:
            chosen = records[0]
        else:
            raise ValueError("JobDiva JobsDetail response is ambiguous")

    normalized = normalize_job(chosen, system="jobdiva")
    requirements = explicit_requirements(chosen)

    required_license_states = [
        req.value for req in requirements if req.kind == "license"
    ]
    normalized = normalized.model_copy(update={
        "hard_requirements": requirements,
        "required_license_states": required_license_states,
    })
    return normalized, JobEnrichmentResult(
        source_job_id=job_id,
        detail_records=len(records),
        requirements=len(requirements),
    )
