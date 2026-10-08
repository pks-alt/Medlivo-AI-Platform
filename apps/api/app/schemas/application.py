from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CareerApplicationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    job_id: UUID
    name: str = Field(min_length=2, max_length=200)
    email: str = Field(min_length=6, max_length=254)
    phone: str | None = Field(default=None, max_length=50)
    profession: str | None = Field(default=None, max_length=200)
    specialty: str | None = Field(default=None, max_length=200)
    preferred_location: str | None = Field(default=None, max_length=200)
    availability: str | None = Field(default=None, max_length=200)
    resume_url: str | None = Field(default=None, max_length=1000)
    consent_to_contact: bool

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        value = value.lower()
        if "@" not in value or "." not in value.rsplit("@", 1)[-1] or any(ch.isspace() for ch in value):
            raise ValueError("A valid email address is required")
        return value

    @field_validator("resume_url")
    @classmethod
    def require_https_resume_url(cls, value):
        if value and not value.startswith("https://"):
            raise ValueError("Resume link must use HTTPS")
        return value

    @field_validator("consent_to_contact")
    @classmethod
    def require_consent(cls, value):
        if value is not True:
            raise ValueError("Consent to contact is required")
        return value


class CareerApplicationReceipt(BaseModel):
    application_id: UUID
    job_id: UUID
    status: str
    candidate_status: str
    ownership_status: str
    recruiter_assigned: bool
