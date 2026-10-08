from __future__ import annotations

from datetime import date
from typing import Any

from matching_engine import (
    CandidateCertification,
    CandidateLicense,
    CandidateMatchInput,
    JobMatchInput,
)


_DIVISIONS = {
    "Nursing & Allied": "nursing_allied",
    "Rehabilitation": "rehabilitation",
    "Locum Tenens": "locum_tenens",
    "nursing_allied": "nursing_allied",
    "rehabilitation": "rehabilitation",
    "locum_tenens": "locum_tenens",
    "non_clinical": "non_clinical",
}


def job_match_input(
    job: dict[str, Any],
    *,
    requirements: list[dict[str, Any]],
) -> JobMatchInput:
    division = _DIVISIONS.get(job.get("division"))

    required_license_states: list[str] = []
    required_certifications: list[str] = []
    care_setting = None
    required_skills: list[str] = []

    for requirement in requirements:
        key = requirement.get("canonical_key")
        raw = requirement.get("value") or {}
        value = raw.get("value") if isinstance(raw, dict) else raw
        if value in (None, ""):
            continue
        text = str(value).strip()
        if key == "license_state" and requirement.get("is_hard_gate"):
            state = text.upper()
            if len(state) == 2 and state not in required_license_states:
                required_license_states.append(state)
        elif key == "certification" and requirement.get("is_hard_gate"):
            if text not in required_certifications:
                required_certifications.append(text)
        elif key == "setting":
            care_setting = care_setting or text
        elif key == "skill":
            if text not in required_skills:
                required_skills.append(text)

    payload = job.get("normalized_payload") or {}
    if not care_setting and isinstance(payload, dict):
        care_setting = payload.get("care_setting")

    return JobMatchInput(
        job_id=str(job["id"]),
        division=division,
        profession=job.get("profession"),
        specialty=job.get("specialty"),
        care_setting=care_setting,
        city=job.get("city"),
        state=job.get("state"),
        start_date=job.get("start_date"),
        required_license_states=required_license_states,
        required_certifications=required_certifications,
        required_skills=required_skills,
    )


def candidate_match_input(
    candidate: dict[str, Any],
    *,
    licenses: list[dict[str, Any]],
    certifications: list[dict[str, Any]],
    availability: dict[str, Any] | None,
    resume_available: bool,
    care_settings: list[str] | None = None,
) -> CandidateMatchInput:
    return CandidateMatchInput(
        candidate_id=str(candidate["id"]),
        profession=candidate.get("profession"),
        specialty=candidate.get("specialty"),
        care_settings=care_settings if care_settings is not None else list(candidate.get("resume_care_settings") or []),
        resume_specialties=list(candidate.get("resume_specialties") or []),
        clinical_skills=list(candidate.get("resume_clinical_skills") or []),
        city=candidate.get("city"),
        state=candidate.get("state"),
        available_from=availability.get("available_from") if availability else None,
        licenses=[
            CandidateLicense(
                license_type=row["license_type"],
                state=row.get("state"),
                status=row.get("status"),
                expires_at=row.get("expires_at"),
            )
            for row in licenses
            if row.get("license_type")
        ],
        certifications=[
            CandidateCertification(
                name=row["certification_name"],
                status=row.get("status"),
                expires_at=row.get("expires_at"),
            )
            for row in certifications
            if row.get("certification_name")
        ],
        resume_available=resume_available,
        profile_readiness=int(candidate.get("profile_freshness") or 0),
    )
