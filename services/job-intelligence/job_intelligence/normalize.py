from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from .models import NormalizedJob, SourceRef


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


def _decimal(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace("$", "").replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None


def _integer(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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


def _state(value):
    text = _text(value)
    if not text:
        return None
    upper = text.upper()
    return upper if len(upper) == 2 else None


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


def normalize_job(payload: dict[str, Any], *, system: str = "jobdiva") -> NormalizedJob:
    """Conservative first-pass normalization.

    The raw source payload is preserved because JobDiva custom-field names and
    healthcare-specific mappings must be learned from Medlivo's real records.
    Unknown fields are never invented or silently discarded.
    """
    source_id = _first(payload, ("jobId", "JOBID", "jobid", "id", "ID"))
    title = _first(payload, ("jobTitle", "JOBTITLE", "title", "TITLE"))
    if source_id in (None, ""):
        raise ValueError("Source job ID is required")
    if title in (None, ""):
        raise ValueError("Job title is required")

    updated = _first(payload, ("updatedAt", "UPDATEDDATE", "dateUpdated", "DATEUPDATED"))
    source_updated_at = None
    if isinstance(updated, datetime):
        source_updated_at = updated
    elif updated:
        try:
            source_updated_at = datetime.fromisoformat(str(updated).replace("Z", "+00:00"))
        except ValueError:
            pass

    return NormalizedJob(
        source=SourceRef(system=system, source_id=str(source_id), source_updated_at=source_updated_at),
        status=_status(_first(payload, ("status", "STATUS", "jobStatus", "JOBSTATUS"))),
        title=str(title).strip(),
        profession=_text(_first(payload, ("profession", "PROFESSION", "jobType", "JOBTYPE"))),
        specialty=_text(_first(payload, ("specialty", "SPECIALTY"))),
        care_setting=_text(_first(payload, ("setting", "SETTING", "careSetting", "CARESETTING"))),
        client_name=_text(_first(payload, ("company", "COMPANY", "clientName", "CLIENTNAME"))),
        facility_name=_text(_first(payload, ("facility", "FACILITY", "facilityName", "FACILITYNAME"))),
        city=_text(_first(payload, ("city", "CITY"))),
        state=_state(_first(payload, ("state", "STATE"))),
        postal_code=_text(_first(payload, ("zip", "ZIP", "postalCode", "POSTALCODE"))),
        shift=_text(_first(payload, ("shift", "SHIFT"))),
        schedule=_text(_first(payload, ("schedule", "SCHEDULE"))),
        start_date=_date(_first(payload, ("startDate", "STARTDATE"))),
        end_date=_date(_first(payload, ("endDate", "ENDDATE"))),
        duration_weeks=_integer(_first(payload, ("durationWeeks", "DURATIONWEEKS"))),
        openings=_integer(_first(payload, ("openings", "OPENINGS", "positions", "POSITIONS"))),
        bill_rate=_decimal(_first(payload, ("billRate", "BILLRATE"))),
        pay_rate_min=_decimal(_first(payload, ("payRateMin", "PAYRATEMIN"))),
        pay_rate_max=_decimal(_first(payload, ("payRateMax", "PAYRATEMAX"))),
        description_text=_text(_first(payload, ("description", "DESCRIPTION", "jobDescription", "JOBDESCRIPTION"))),
        source_fields=dict(payload),
    )
