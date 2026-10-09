from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Iterable

from job_intelligence import classify_division


def _first(payload: dict[str, Any], names: Iterable[str]):
    for name in names:
        value = payload.get(name)
        if value not in (None, ""):
            return value
    return None


def _text(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _state(value):
    text = _text(value)
    if not text:
        return None
    value = text.upper()
    return value if len(value) == 2 else None


def _date(value):
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    for parser in (
        lambda: datetime.fromisoformat(text.replace("Z", "+00:00")).date(),
        lambda: datetime.strptime(text, "%m/%d/%Y").date(),
        lambda: datetime.strptime(text, "%Y-%m-%d").date(),
    ):
        try:
            return parser()
        except ValueError:
            pass
    return None


def _status(value):
    text = (_text(value) or "").lower()
    if text in {"open", "active", "opened"}:
        return "open"
    if text in {"hold", "on hold", "on_hold"}:
        return "on_hold"
    if text in {"closed", "filled"}:
        return "closed"
    if text in {"cancelled", "canceled"}:
        return "cancelled"
    return "unknown"


@dataclass(frozen=True)
class JobPromotion:
    source_id: str
    title: str
    profession: str | None
    specialty: str | None
    division: str | None
    city: str | None
    state: str | None
    start_date: date | None
    status: str
    normalized_payload: dict[str, Any]


@dataclass(frozen=True)
class CandidatePromotion:
    source_id: str
    canonical_name: str | None
    primary_email: str | None
    primary_phone: str | None
    profession: str | None
    specialty: str | None
    city: str | None
    state: str | None
    canonical_profile: dict[str, Any]


def promote_job_payload(payload: dict[str, Any]) -> JobPromotion:
    source_id = _first(payload, ("JOBID", "jobId", "jobID", "id", "ID"))
    title = _first(payload, ("JOBTITLE", "jobTitle", "title", "TITLE"))
    if source_id in (None, ""):
        raise ValueError("Source job ID is required")
    if title in (None, ""):
        raise ValueError("Job title is required")

    normalized = {
        "source_system": "jobdiva",
        "source_id": str(source_id),
        "source_fields_present": sorted(str(k) for k, v in payload.items() if v not in (None, "")),
    }
    return JobPromotion(
        source_id=str(source_id),
        title=str(title).strip(),
        profession=_text(_first(payload, ("PROFESSION", "profession", "JOBTYPE", "jobType"))),
        specialty=_text(_first(payload, ("SPECIALTY", "specialty"))),
        division=classify_division(payload),
        city=_text(_first(payload, ("CITY", "city"))),
        state=_state(_first(payload, ("STATE", "state"))),
        start_date=_date(_first(payload, ("STARTDATE", "startDate"))),
        status=_status(_first(payload, ("STATUS", "status", "JOBSTATUS", "jobStatus"))),
        normalized_payload=normalized,
    )


def _candidate_name(payload: dict[str, Any]) -> str | None:
    full = _text(_first(payload, ("FULLNAME", "fullName", "CANDIDATENAME", "candidateName", "NAME", "name")))
    if full:
        return full
    first = _text(_first(payload, ("FIRSTNAME", "firstName", "first_name")))
    last = _text(_first(payload, ("LASTNAME", "lastName", "last_name")))
    combined = " ".join(part for part in (first, last) if part)
    return combined or None


def promote_candidate_payload(payload: dict[str, Any]) -> CandidatePromotion:
    source_id = _first(payload, ("CANDIDATEID", "candidateId", "candidateID", "id", "ID"))
    if source_id in (None, ""):
        raise ValueError("Source candidate ID is required")

    profile = {
        "source_system": "jobdiva",
        "source_id": str(source_id),
        "promotion_scope": "delta_explicit_fields_only",
        "source_fields_present": sorted(str(k) for k, v in payload.items() if v not in (None, "")),
    }
    return CandidatePromotion(
        source_id=str(source_id),
        canonical_name=_candidate_name(payload),
        primary_email=_text(_first(payload, ("EMAIL", "email", "EMAILADDRESS", "emailAddress"))),
        primary_phone=_text(_first(payload, ("PHONE", "phone", "MOBILEPHONE", "mobilePhone", "CELLPHONE", "cellPhone"))),
        profession=_text(_first(payload, ("PROFESSION", "profession", "CANDIDATETYPE", "candidateType", "JOBTYPE", "jobType"))),
        specialty=_text(_first(payload, ("SPECIALTY", "specialty", "PRIMARYSPECIALTY", "primarySpecialty"))),
        city=_text(_first(payload, ("CITY", "city"))),
        state=_state(_first(payload, ("STATE", "state"))),
        canonical_profile=profile,
    )
