from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from job_intelligence import NormalizedJob, SourceRef, analyze_job


DIVISION_MAP = {
    "Rehabilitation": "rehabilitation",
    "Nursing & Allied": "nursing_allied",
    "Locum Tenens": "locum_tenens",
}


def _date_value(value: Any):
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _decimal_value(value: Any):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def analyze_intake_job(normalized: dict[str, Any], *, division: str, source_id: str,
                       customer_name: str) -> dict[str, Any]:
    """Bridge direct-customer intake into the canonical Job Intelligence service.

    This module only adapts intake field names. All readiness, conflict,
    provenance and standardized-JD rules remain owned by job-intelligence.
    """
    canonical_division = DIVISION_MAP.get(division)
    if canonical_division is None:
        raise ValueError("Unsupported Medlivo division")

    title = str(normalized.get("title") or "").strip()
    if not title:
        # The intake validator will already route this row to review. A
        # placeholder is used only to satisfy the strict canonical model while
        # preserving the missing-title error; it is never approved as source data.
        title = "Missing job title"

    bill_rate = _decimal_value(normalized.get("bill_rate"))

    job = NormalizedJob(
        source=SourceRef(system="direct_customer", source_id=source_id),
        status="open",
        title=title,
        division=canonical_division,
        profession=normalized.get("profession"),
        specialty=normalized.get("specialty"),
        care_setting=normalized.get("setting"),
        client_name=customer_name,
        facility_name=normalized.get("facility"),
        city=normalized.get("city"),
        state=normalized.get("state"),
        shift=normalized.get("shift"),
        schedule=normalized.get("schedule"),
        start_date=_date_value(normalized.get("start_date")),
        end_date=_date_value(normalized.get("end_date")),
        duration_weeks=normalized.get("duration_weeks"),
        openings=normalized.get("providers_needed") or normalized.get("openings"),
        bill_rate=bill_rate,
        rate_unit="hour" if bill_rate is not None else "unknown",
        description_text=normalized.get("description"),
        source_fields=dict(normalized),
    )

    review = analyze_job(job)
    result = review.as_dict()

    # Direct-customer rows are source-confirmed only for fields actually present
    # in the spreadsheet. Division/customer are workflow context, not customer
    # source values.
    present = set(normalized)
    result["provenance"] = [
        item for item in result["provenance"]
        if item["field"] in present or item["field"] in {"division", "client_name"}
    ]
    result["extracted_values"] = dict(normalized)
    result["ai_suggestions"] = []
    return result
