from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from .models import NormalizedJob
from .templates import build_publishable_draft


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
        conflicts.append(JobConflict("profession_title_conflict", "profession",
                                     "Job title indicates Physical Therapist but profession differs."))
    if "registered nurse" in title and profession and "nurs" not in profession and profession != "rn":
        conflicts.append(JobConflict("profession_title_conflict", "profession",
                                     "Job title indicates Registered Nurse but profession differs."))
    if job.required_license_states and job.state and job.state not in job.required_license_states:
        conflicts.append(JobConflict("license_state_conflict", "required_license_states",
                                     "Required license state does not include the job state."))
    if specialty and "icu" in title and "icu" not in specialty and "critical" not in specialty:
        conflicts.append(JobConflict("specialty_title_conflict", "specialty",
                                     "Job title indicates ICU but specialty differs."))
    return conflicts


def analyze_job(job: NormalizedJob) -> JobReviewResult:
    missing = [field for field in _required_fields(job) if getattr(job, field, None) in (None, "", [])]
    conflicts = _conflicts(job)

    # Bill rate policy: source value is confirmed; absent value remains unknown.
    bill_rate_state = "confirmed" if job.bill_rate is not None else "unknown"

    recruiting_ready = not missing and not conflicts
    commercial_ready = recruiting_ready and bill_rate_state == "confirmed"

    draft = build_publishable_draft(job)
    internal_jd = {
        "title": draft.public_title,
        "summary": draft.summary,
        "sections": [section.model_dump(mode="json") for section in draft.sections],
        "quality": draft.quality.model_dump(mode="json"),
        "review_required": bool(missing or conflicts or any(s.requires_confirmation for s in draft.sections)),
    }

    return JobReviewResult(
        missing_fields=missing,
        conflicts=conflicts,
        provenance=_provenance(job),
        recruiting_readiness="ready" if recruiting_ready else "review",
        commercial_readiness="ready" if commercial_ready else "review",
        bill_rate_state=bill_rate_state,
        standardized_internal_jd=internal_jd,
    )
