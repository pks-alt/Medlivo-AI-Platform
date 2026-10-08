from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SyncStreamHealth(BaseModel):
    tenant_slug: str
    source_system: str
    stream: Literal["jobs", "candidates"]
    status: Literal["healthy", "stale", "error", "never_synced"]
    watermark: datetime | None = None
    last_success_at: datetime | None = None
    last_run_status: str | None = None
    last_run_started_at: datetime | None = None
    last_run_finished_at: datetime | None = None
    last_error_code: str | None = None
    freshness_minutes: int | None = None
    latest_records_seen: int | None = None
    latest_records_upserted: int | None = None


class JobDivaSyncHealth(BaseModel):
    generated_at: datetime
    streams: list[SyncStreamHealth]
