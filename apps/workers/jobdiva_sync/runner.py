from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from uuid import uuid4

from .models import SyncRunSummary, SyncStream


class DeltaClient(Protocol):
    async def updated_jobs(self, *, from_date: datetime, to_date: datetime, page_number: int, page_size: int) -> list[dict[str, Any]]: ...
    async def updated_candidates(self, *, from_date: datetime, to_date: datetime, page_number: int, page_size: int) -> list[dict[str, Any]]: ...


class SyncStore(Protocol):
    async def checkpoint(self, tenant_id: str, source_system: str, stream: SyncStream) -> datetime | None: ...
    async def start_run(self, *, run_id: str, tenant_id: str, source_system: str, stream: SyncStream, window_start: datetime, window_end: datetime) -> None: ...
    async def upsert_page(self, *, tenant_id: str, source_system: str, stream: SyncStream, records: list[dict[str, Any]]) -> int: ...
    async def succeed_run(self, *, run_id: str, tenant_id: str, source_system: str, stream: SyncStream, window_end: datetime, pages_processed: int, records_seen: int, records_upserted: int) -> None: ...
    async def fail_run(self, *, run_id: str, tenant_id: str, source_system: str, stream: SyncStream, error_code: str, pages_processed: int, records_seen: int, records_upserted: int) -> None: ...


_ID_KEYS = {
    SyncStream.JOBS: ("JOBID", "jobId", "jobID", "id", "ID"),
    SyncStream.CANDIDATES: ("CANDIDATEID", "candidateId", "candidateID", "id", "ID"),
}


def source_id(stream: SyncStream, record: dict[str, Any]) -> str:
    for key in _ID_KEYS[stream]:
        value = record.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (str, int)) and str(value).strip():
            return str(value).strip()
    raise ValueError(f"JobDiva {stream.value} delta record is missing a source ID")


def validate_page(stream: SyncStream, records: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for record in records:
        ident = source_id(stream, record)
        if ident in seen:
            continue
        seen.add(ident)


async def run_delta_sync(
    client: DeltaClient,
    store: SyncStore,
    *,
    tenant_id: str,
    stream: SyncStream,
    now: datetime | None = None,
    overlap: timedelta = timedelta(minutes=5),
    initial_lookback: timedelta = timedelta(days=1),
    safety_lag: timedelta = timedelta(minutes=2),
    page_size: int = 100,
    max_pages: int = 1000,
) -> SyncRunSummary:
    """Run one replay-safe JobDiva delta window.

    The checkpoint advances only after the whole window succeeds. A failed run
    is replayed from the previous watermark on the next attempt, while source
    table uniqueness makes page replays idempotent.
    """
    if page_size < 1 or page_size > 1000:
        raise ValueError("page_size must be between 1 and 1000")
    if max_pages < 1:
        raise ValueError("max_pages must be positive")

    source_system = "jobdiva"
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    watermark = await store.checkpoint(tenant_id, source_system, stream)
    window_start = (watermark - overlap) if watermark else (current - initial_lookback)
    window_end = current - safety_lag
    if window_end <= window_start:
        window_end = current

    run_id = str(uuid4())
    await store.start_run(
        run_id=run_id,
        tenant_id=tenant_id,
        source_system=source_system,
        stream=stream,
        window_start=window_start,
        window_end=window_end,
    )

    pages = seen = upserted = 0
    try:
        for page_number in range(1, max_pages + 1):
            if stream == SyncStream.JOBS:
                records = await client.updated_jobs(
                    from_date=window_start,
                    to_date=window_end,
                    page_number=page_number,
                    page_size=page_size,
                )
            else:
                records = await client.updated_candidates(
                    from_date=window_start,
                    to_date=window_end,
                    page_number=page_number,
                    page_size=page_size,
                )

            validate_page(stream, records)
            if not records:
                break

            page_upserted = await store.upsert_page(
                tenant_id=tenant_id,
                source_system=source_system,
                stream=stream,
                records=records,
            )
            pages += 1
            seen += len(records)
            upserted += page_upserted

            if len(records) < page_size:
                break
        else:
            raise RuntimeError("JobDiva delta pagination reached the configured safety ceiling")

        await store.succeed_run(
            run_id=run_id,
            tenant_id=tenant_id,
            source_system=source_system,
            stream=stream,
            window_end=window_end,
            pages_processed=pages,
            records_seen=seen,
            records_upserted=upserted,
        )
        return SyncRunSummary(
            run_id=run_id,
            stream=stream,
            window_start=window_start,
            window_end=window_end,
            pages_processed=pages,
            records_seen=seen,
            records_upserted=upserted,
        )
    except Exception as exc:
        await store.fail_run(
            run_id=run_id,
            tenant_id=tenant_id,
            source_system=source_system,
            stream=stream,
            error_code=type(exc).__name__[:120],
            pages_processed=pages,
            records_seen=seen,
            records_upserted=upserted,
        )
        raise
