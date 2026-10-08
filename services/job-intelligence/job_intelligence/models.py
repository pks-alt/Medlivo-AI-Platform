from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Division = Literal["nursing_allied", "rehabilitation", "locum_tenens", "non_clinical"]
JobStatus = Literal["open", "on_hold", "closed", "cancelled", "unknown"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SourceRef(StrictModel):
    system: str = "jobdiva"
    source_id: str = Field(min_length=1, max_length=128)
    source_updated_at: datetime | None = None


class JobRequirement(StrictModel):
    kind: Literal[
        "license", "certification", "experience", "skill", "setting",
        "schedule", "education", "credential", "other"
    ]
    value: str = Field(min_length=1, max_length=300)
    required: bool = True
    source_field: str | None = Field(default=None, max_length=200)


class JobPreference(StrictModel):
    kind: Literal[
        "license", "certification", "experience", "skill", "setting",
        "schedule", "language", "distance", "other"
    ]
    value: str = Field(min_length=1, max_length=300)
    source_field: str | None = Field(default=None, max_length=200)


class NormalizedJob(StrictModel):
    source: SourceRef
    status: JobStatus = "unknown"
    title: str = Field(min_length=1, max_length=300)
    division: Division | None = None
    profession: str | None = Field(default=None, max_length=200)
    specialty: str | None = Field(default=None, max_length=200)
    care_setting: str | None = Field(default=None, max_length=200)

    client_name: str | None = Field(default=None, max_length=300)
    facility_name: str | None = Field(default=None, max_length=300)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, min_length=2, max_length=2)
    postal_code: str | None = Field(default=None, max_length=20)
    required_license_states: list[str] = Field(default_factory=list)

    shift: str | None = Field(default=None, max_length=120)
    schedule: str | None = Field(default=None, max_length=300)
    start_date: date | None = None
    end_date: date | None = None
    duration_weeks: int | None = Field(default=None, ge=1, le=260)

    openings: int | None = Field(default=None, ge=0, le=10000)
    bill_rate: Decimal | None = Field(default=None, ge=0)
    pay_rate_min: Decimal | None = Field(default=None, ge=0)
    pay_rate_max: Decimal | None = Field(default=None, ge=0)
    rate_unit: Literal["hour", "day", "shift", "week", "flat", "unknown"] = "unknown"

    remote_allowed: bool | None = None
    travel_required: bool | None = None

    hard_requirements: list[JobRequirement] = Field(default_factory=list)
    preferences: list[JobPreference] = Field(default_factory=list)

    description_text: str | None = None
    source_fields: dict[str, Any] = Field(default_factory=dict)

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value):
        return value.upper() if value else value

    @field_validator("required_license_states")
    @classmethod
    def normalize_license_states(cls, values):
        result = []
        for value in values:
            state = value.strip().upper()
            if len(state) != 2:
                raise ValueError("License states must use two-letter abbreviations")
            if state not in result:
                result.append(state)
        return result

    @field_validator("pay_rate_max")
    @classmethod
    def validate_pay_range(cls, value, info):
        minimum = info.data.get("pay_rate_min")
        if value is not None and minimum is not None and value < minimum:
            raise ValueError("pay_rate_max must be greater than or equal to pay_rate_min")
        return value


ContentProvenance = Literal["source_confirmed", "medlivo_standard", "ai_suggested"]
PublishReadiness = Literal["not_ready", "manager_review", "ready_for_recruiting", "ready_to_publish"]


class JobContentSection(StrictModel):
    key: str = Field(min_length=1, max_length=80)
    heading: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=6000)
    provenance: ContentProvenance
    requires_confirmation: bool = False


class JobQualityScore(StrictModel):
    overall: int = Field(ge=0, le=100)
    core_data: int = Field(ge=0, le=100)
    matching_readiness: int = Field(ge=0, le=100)
    publishing_readiness: int = Field(ge=0, le=100)
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PublishableJobDraft(StrictModel):
    template_id: str = Field(min_length=1, max_length=120)
    division: Division
    profession: str | None = None
    specialty: str | None = None
    public_title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=2000)
    sections: list[JobContentSection]
    public_fields: dict[str, Any] = Field(default_factory=dict)
    internal_fields: dict[str, Any] = Field(default_factory=dict)
    quality: JobQualityScore
    readiness: PublishReadiness
