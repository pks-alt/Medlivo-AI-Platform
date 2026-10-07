from datetime import datetime
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
    role: Literal["admin", "manager", "recruiter", "operations"]
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
    role: Literal["admin", "manager", "recruiter", "operations"]
    team_id: UUID | None = None
    is_active: bool
