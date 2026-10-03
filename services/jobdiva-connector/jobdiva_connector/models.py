from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SourceEnvelope(BaseModel):
    source: str = "jobdiva"
    source_id: str
    source_updated_at: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class JobSourceRecord(SourceEnvelope):
    entity_type: str = "job"


class CandidateSourceRecord(SourceEnvelope):
    entity_type: str = "candidate"


class ResumeSourceRecord(SourceEnvelope):
    entity_type: str = "resume"
    candidate_source_id: str | None = None


class WebhookEvent(BaseModel):
    entity: str
    operation: str
    source_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
