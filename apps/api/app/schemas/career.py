from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


Division = Literal["nursing_allied", "rehabilitation", "locum_tenens"]


class PublicJobSection(BaseModel):
    model_config = ConfigDict(extra="ignore")
    key: str
    heading: str
    content: str


class PublicJobListItem(BaseModel):
    id: UUID
    title: str
    summary: str
    division: Division
    profession: str | None = None
    specialty: str | None = None
    city: str | None = None
    state: str | None = None
    care_setting: str | None = None
    shift: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    duration_weeks: int | None = None
    openings: int | None = None
    rate_unit: str | None = None


class PublicJobDetail(PublicJobListItem):
    sections: list[PublicJobSection] = Field(default_factory=list)
    public_fields: dict[str, Any] = Field(default_factory=dict)


class PublicJobPage(BaseModel):
    items: list[PublicJobListItem]
    next_cursor: UUID | None = None
