from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class SyncStream(StrEnum):
    JOBS = "jobs"
    CANDIDATES = "candidates"


@dataclass(frozen=True)
class SyncCheckpoint:
    watermark: datetime | None


@dataclass(frozen=True)
class SyncRunSummary:
    run_id: str
    stream: SyncStream
    window_start: datetime
    window_end: datetime
    pages_processed: int
    records_seen: int
    records_upserted: int
