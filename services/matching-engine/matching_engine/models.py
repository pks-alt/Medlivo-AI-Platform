from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CandidateLicense(StrictModel):
    license_type: str
    state: str | None = None
    status: str | None = None
    expires_at: date | None = None


class CandidateCertification(StrictModel):
    name: str
    status: str | None = None
    expires_at: date | None = None


class CandidateMatchInput(StrictModel):
    candidate_id: str
    profession: str | None = None
    specialty: str | None = None
    care_settings: list[str] = Field(default_factory=list)
    city: str | None = None
    state: str | None = None
    available_from: date | None = None
    licenses: list[CandidateLicense] = Field(default_factory=list)
    certifications: list[CandidateCertification] = Field(default_factory=list)
    resume_available: bool = False
    profile_readiness: int = Field(default=0, ge=0, le=100)


class JobMatchInput(StrictModel):
    job_id: str
    division: Literal["nursing_allied", "rehabilitation", "locum_tenens", "non_clinical"]
    profession: str | None = None
    specialty: str | None = None
    care_setting: str | None = None
    city: str | None = None
    state: str | None = None
    start_date: date | None = None
    required_license_states: list[str] = Field(default_factory=list)
    required_certifications: list[str] = Field(default_factory=list)


class MatchGate(StrictModel):
    key: str
    passed: bool
    reason: str


class ScoreComponent(StrictModel):
    key: str
    score: float = Field(ge=0, le=10)
    weight: float = Field(ge=0)
    reason: str


class MatchResult(StrictModel):
    job_id: str
    candidate_id: str
    eligible: bool
    score: float = Field(ge=0, le=10)
    gates: list[MatchGate]
    components: list[ScoreComponent]
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
