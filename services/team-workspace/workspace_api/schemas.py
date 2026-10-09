from datetime import datetime, date
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class MatchFeedbackInput(StrictInput):
    feedback_code: Literal["strong_match", "good_match", "weak_match", "not_a_match"]
    reason_code: Literal[
        "license", "certification", "specialty", "care_setting", "experience",
        "availability", "location", "compensation", "other"
    ] | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def negative_feedback_needs_reason(self):
        if self.feedback_code in {"weak_match", "not_a_match"} and self.reason_code is None:
            raise ValueError("A reason is required for weak or not-a-match feedback")
        return self


class JobOperationalUpdate(StrictInput):
    client_priority: Literal["high", "normal", "low"] = "normal"
    job_priority: Literal["hot", "priority", "standard", "hold"] = "standard"
    priority_reason: str | None = Field(default=None, max_length=1000)
    manager_note: str | None = Field(default=None, max_length=2000)
    next_action: str | None = Field(default=None, max_length=500)
    due_at: datetime | None = None
    operational_status: Literal["active", "hold", "closed"] = "active"
    expected_version: int = Field(ge=0)

    @field_validator("due_at")
    @classmethod
    def operational_due_requires_zone(cls, value):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("A timezone-aware deadline is required")
        return value


class JobAssignmentInput(StrictInput):
    recruiter_user_id: UUID | None = None
    team_id: UUID
    reason: str = Field(min_length=5, max_length=1000)
    expected_version: int = Field(ge=0)


class JobIntakeItemDecision(StrictInput):
    decision: Literal["approved", "rejected"]
    final_approved_values: dict | None = None
    bill_rate_state: Literal["confirmed", "suggested", "unknown"] = "unknown"
    recruiting_readiness: Literal["not_ready", "review", "ready"] = "review"
    commercial_readiness: Literal["not_ready", "review", "ready"] = "review"
    reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def intake_rejection_requires_reason(self):
        if self.decision == "rejected" and not self.reason:
            raise ValueError("A rejection reason is required")
        return self


class ApprovalDecisionInput(StrictInput):
    decision: Literal["approved", "rejected", "cancelled"]
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def approval_rejection_requires_notes(self):
        if self.decision == "rejected" and not self.notes:
            raise ValueError("A rejection reason is required")
        return self
