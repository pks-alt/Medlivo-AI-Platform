from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CandidateEvidence(StrictModel):
    fact_key: str
    value: Any
    source_type: Literal["jobdiva_profile", "jobdiva_license", "jobdiva_certification", "jobdiva_resume"]
    source_reference: str | None = None
    confidence: float = Field(default=1.0, ge=0, le=1)


class LicenseIntelligence(StrictModel):
    license_type: str
    state: str | None = None
    license_number: str | None = None
    status: str | None = None
    expires_at: date | None = None
    source_reference: str | None = None

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value):
        value = value.upper() if value else value
        return value if not value or len(value) == 2 else None


class CertificationIntelligence(StrictModel):
    name: str
    status: str | None = None
    expires_at: date | None = None
    source_reference: str | None = None


class ResumeIntelligence(StrictModel):
    source_resume_id: str
    resume_date: datetime | None = None
    text: str | None = None
    source_reference: str | None = None


class MatchingReadiness(StrictModel):
    score: int = Field(ge=0, le=100)
    identity_complete: bool
    contact_complete: bool
    profession_complete: bool
    credential_signal: bool
    resume_available: bool
    missing_fields: list[str] = Field(default_factory=list)


class CandidateIntelligence(StrictModel):
    source_system: str = "jobdiva"
    source_candidate_id: str
    source_updated_at: datetime | None = None

    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    profession: str | None = None
    specialty: str | None = None
    city: str | None = None
    state: str | None = None

    licenses: list[LicenseIntelligence] = Field(default_factory=list)
    certifications: list[CertificationIntelligence] = Field(default_factory=list)
    resumes: list[ResumeIntelligence] = Field(default_factory=list)
    primary_resume_id: str | None = None

    matching_readiness: MatchingReadiness
    evidence: list[CandidateEvidence] = Field(default_factory=list)
    source_profile: dict[str, Any] = Field(default_factory=dict)

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value):
        value = value.upper() if value else value
        return value if not value or len(value) == 2 else None


class JobDivaCandidateBundle(StrictModel):
    candidate_id: str
    source_updated_at: datetime | None = None
    profile_records: list[dict[str, Any]] = Field(default_factory=list)
    license_records: list[dict[str, Any]] = Field(default_factory=list)
    certification_records: list[dict[str, Any]] = Field(default_factory=list)
    resume_records: list[dict[str, Any]] = Field(default_factory=list)
    resume_text_records: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
