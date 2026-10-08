from datetime import datetime, date
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, hide_input_in_errors=True)


class NoteInput(StrictInput):
    body: str = Field(min_length=1, max_length=4000)


class TaskInput(StrictInput):
    title: str = Field(min_length=1, max_length=250)
    due_at: datetime

    @field_validator("due_at")
    @classmethod
    def require_zone(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("A timezone-aware deadline is required")
        return value


class TaskUpdate(StrictInput):
    status: Literal["open", "done"]
    expected_version: int = Field(ge=1)


class Reassignment(StrictInput):
    owner_user_id: UUID
    reason: str = Field(min_length=5, max_length=500)
    expected_version: int = Field(ge=1)


class AdminUserInput(StrictInput):
    email: str = Field(min_length=6, max_length=320)
    display_name: str = Field(min_length=1, max_length=200)
    role: Literal["admin", "manager", "recruiter"]
    team_id: UUID | None = None
    is_active: bool = True

    @field_validator("email")
    @classmethod
    def require_medlivo_email(cls, value):
        value = value.lower()
        if not value.endswith("@medlivo.com") or any(ch.isspace() for ch in value):
            raise ValueError("Use an approved Medlivo email address")
        return value


class AdminUserUpdate(StrictInput):
    display_name: str = Field(min_length=1, max_length=200)
    role: Literal["admin", "manager", "recruiter"]
    team_id: UUID | None = None
    is_active: bool


class JobIntakeBatchInput(StrictInput):
    customer_name: str = Field(min_length=1, max_length=200)
    division: Literal["Rehabilitation", "Nursing & Allied", "Locum Tenens"]
    source_filename: str = Field(min_length=1, max_length=255)
    team_id: UUID | None = None
    mapping: dict[str, str] = Field(default_factory=dict)


class CustomerJobMappingInput(StrictInput):
    customer_name: str = Field(min_length=1, max_length=200)
    division: Literal["Rehabilitation", "Nursing & Allied", "Locum Tenens"]
    mapping: dict[str, str]


class WeeklyGoalInput(StrictInput):
    week_start: date
    submissions_target: int = Field(ge=0, le=1000)
    interviews_target: int = Field(ge=0, le=1000)
    closures_target: int = Field(ge=0, le=1000)
    priority_jobs_target: int = Field(default=0, ge=0, le=1000)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("week_start")
    @classmethod
    def require_monday(cls, value):
        if value.weekday() != 0:
            raise ValueError("week_start must be a Monday")
        return value


class JobIntakeRowsInput(StrictInput):
    rows: list[dict[str, str | int | float | bool | None]] = Field(min_length=1, max_length=500)
    mapping: dict[str, str] | None = None


class JobPublicationDraftInput(StrictInput):
    team_id: UUID | None = None
    job_id: UUID | None = None
    intake_item_id: UUID | None = None
    source_snapshot: dict
    enhanced_snapshot: dict
    quality_score: dict
    readiness: Literal["not_ready", "manager_review", "ready_for_recruiting", "ready_to_publish"]

    @field_validator("intake_item_id")
    @classmethod
    def require_one_source(cls, value, info):
        job_id = info.data.get("job_id")
        if (job_id is None) == (value is None):
            raise ValueError("Provide exactly one of job_id or intake_item_id")
        return value


class JobPublicationDecision(StrictInput):
    target: Literal["recruiting", "website"]
    decision: Literal["approved", "rejected"]
    reason: str | None = Field(default=None, max_length=1000)
    expected_version: int = Field(ge=1)

    @field_validator("reason")
    @classmethod
    def rejection_needs_reason(cls, value, info):
        if info.data.get("decision") == "rejected" and not value:
            raise ValueError("A rejection reason is required")
        return value


class CareerApplicationAssignment(StrictInput):
    recruiter_user_id: UUID
    reason: str = Field(min_length=3, max_length=500)
