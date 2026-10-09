from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from .models import NormalizedJob


@dataclass(frozen=True)
class FieldProvenance:
    field: str
    source_type: str
    source_reference: str | None
    confidence: float


@dataclass(frozen=True)
class JobConflict:
    code: str
    field: str
    message: str


@dataclass(frozen=True)
class JobReviewResult:
    missing_fields: list[str]
    conflicts: list[JobConflict]
    provenance: list[FieldProvenance]
    recruiting_readiness: str
    commercial_readiness: str
    bill_rate_state: str
    standardized_internal_jd: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "missing_fields": self.missing_fields,
            "conflicts": [asdict(x) for x in self.conflicts],
            "provenance": [asdict(x) for x in self.provenance],
            "recruiting_readiness": self.recruiting_readiness,
            "commercial_readiness": self.commercial_readiness,
            "bill_rate_state": self.bill_rate_state,
            "standardized_internal_jd": self.standardized_internal_jd,
        }


def _required_fields(job: NormalizedJob) -> list[str]:
    base = ["title", "division", "profession", "city", "state", "start_date"]
    if job.division == "rehabilitation":
        base += ["specialty"]
    elif job.division == "nursing_allied":
        base += ["specialty", "shift"]
    elif job.division == "locum_tenens":
        base += ["specialty", "schedule"]
    return base


def _provenance(job: NormalizedJob) -> list[FieldProvenance]:
    rows: list[FieldProvenance] = []
    for field in (
        "title", "division", "profession", "specialty", "care_setting",
        "client_name", "facility_name", "city", "state", "shift", "schedule",
        "start_date", "end_date", "duration_weeks", "openings", "bill_rate",
    ):
        if getattr(job, field, None) is not None:
            rows.append(FieldProvenance(
                field=field,
                source_type="source_confirmed",
                source_reference=f"{job.source.system}:{job.source.source_id}",
                confidence=1.0,
            ))
    return rows


def _conflicts(job: NormalizedJob) -> list[JobConflict]:
    conflicts: list[JobConflict] = []
    title = job.title.lower()
    profession = (job.profession or "").lower()
    specialty = (job.specialty or "").lower()

    if "physical therapist" in title and profession and "physical" not in profession and profession not in {"pt", "therapist"}:
        conflicts.append(JobConflict(
            "profession_title_conflict", "profession",
            "Job title indicates Physical Therapist but profession differs.",
        ))
    if "registered nurse" in title and profession and "nurs" not in profession and profession != "rn":
        conflicts.append(JobConflict(
            "profession_title_conflict", "profession",
            "Job title indicates Registered Nurse but profession differs.",
        ))
    if job.required_license_states and job.state and job.state not in job.required_license_states:
        conflicts.append(JobConflict(
            "license_state_conflict", "required_license_states",
            "Required license state does not include the job state.",
        ))
    if specialty and "icu" in title and "icu" not in specialty and "critical" not in specialty:
        conflicts.append(JobConflict(
            "specialty_title_conflict", "specialty",
            "Job title indicates ICU but specialty differs.",
        ))
    return conflicts


def _internal_jd(job: NormalizedJob, missing: list[str], conflicts: list[JobConflict],
                 bill_rate_state: str) -> dict[str, Any]:
    """Build the recruiter/manager JD from confirmed facts only.

    This intentionally does not reuse the public marketing template. It may
    structure or restate source facts, but it does not invent responsibilities,
    credentials, hours, compensation, or client requirements.
    """
    location = ", ".join(x for x in (job.city, job.state) if x) or None

    assignment = {
        key: value for key, value in {
            "start_date": job.start_date.isoformat() if job.start_date else None,
            "end_date": job.end_date.isoformat() if job.end_date else None,
            "duration_weeks": job.duration_weeks,
            "shift": job.shift,
            "schedule": job.schedule,
            "openings": job.openings,
            "care_setting": job.care_setting,
            "remote_allowed": job.remote_allowed,
            "travel_required": job.travel_required,
        }.items() if value is not None
    }

    required = [
        {
            "kind": requirement.kind,
            "value": requirement.value,
            "source_field": requirement.source_field,
            "provenance": "source_confirmed",
        }
        for requirement in job.hard_requirements
    ]
    if job.required_license_states:
        required.append({
            "kind": "license",
            "value": "Required license state(s): " + ", ".join(job.required_license_states),
            "source_field": None,
            "provenance": "source_confirmed",
        })

    preferred = [
        {
            "kind": preference.kind,
            "value": preference.value,
            "source_field": preference.source_field,
            "provenance": "source_confirmed",
        }
        for preference in job.preferences
    ]

    commercial = {"bill_rate_state": bill_rate_state}
    if bill_rate_state == "confirmed" and job.bill_rate is not None:
        commercial["bill_rate"] = str(job.bill_rate)
        commercial["rate_unit"] = job.rate_unit

    return {
        "job_title": job.title,
        "location": location,
        "division": job.division,
        "profession": job.profession,
        "specialty": job.specialty,
        "facility": job.facility_name,
        "assignment_details": assignment,
        "required_qualifications": required,
        "preferred_qualifications": preferred,
        "source_description": job.description_text,
        "commercial": commercial,
        "missing_fields": missing,
        "conflicts": [asdict(x) for x in conflicts],
        "review_required": bool(missing or conflicts),
        "source_reference": f"{job.source.system}:{job.source.source_id}",
    }


def analyze_job(job: NormalizedJob) -> JobReviewResult:
    missing = [
        field for field in _required_fields(job)
        if getattr(job, field, None) in (None, "", [])
    ]
    conflicts = _conflicts(job)

    # Bill rate policy: a source value is confirmed. An absent value remains
    # unknown. Suggestions are a separate, human-reviewed workflow.
    bill_rate_state = "confirmed" if job.bill_rate is not None else "unknown"

    recruiting_ready = not missing and not conflicts
    commercial_ready = recruiting_ready and bill_rate_state == "confirmed"

    return JobReviewResult(
        missing_fields=missing,
        conflicts=conflicts,
        provenance=_provenance(job),
        recruiting_readiness="ready" if recruiting_ready else "review",
        commercial_readiness="ready" if commercial_ready else "review",
        bill_rate_state=bill_rate_state,
        standardized_internal_jd=_internal_jd(job, missing, conflicts, bill_rate_state),
    )
