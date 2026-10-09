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
    async def start_run(self, *, run_id: str, tenant_id: str, source_system: str, stream: SyncStream, mode: str, window_start: datetime, window_end: datetime) -> None: ...
    async def upsert_page(self, *, tenant_id: str, source_system: str, stream: SyncStream, records: list[dict[str, Any]]) -> int: ...
    async def succeed_run(self, *, run_id: str, tenant_id: str, source_system: str, stream: SyncStream, window_end: datetime, pages_processed: int, records_seen: int, records_upserted: int) -> None: ...
    async def fail_run(self, *, run_id: str, tenant_id: str, source_system: str, stream: SyncStream, error_code: str, pages_processed: int, records_seen: int, records_upserted: int) -> None: ...
    async def complete_backfill_run(self, *, run_id: str, tenant_id: str, stream: SyncStream, pages_processed: int, records_seen: int, records_upserted: int) -> None: ...
    async def backfill_window_succeeded(self, *, tenant_id: str, source_system: str, stream: SyncStream, window_start: datetime, window_end: datetime) -> bool: ...


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
        mode="delta",
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



async def run_backfill_window(
    client: DeltaClient,
    store: SyncStore,
    *,
    tenant_id: str,
    stream: SyncStream,
    window_start: datetime,
    window_end: datetime,
    page_size: int = 100,
    max_pages: int = 1000,
    source_ids_sink: set[str] | None = None,
) -> SyncRunSummary:
    """Run one explicit historical window without changing the live delta checkpoint."""
    if window_start.tzinfo is None or window_start.utcoffset() is None:
        raise ValueError("window_start must be timezone-aware")
    if window_end.tzinfo is None or window_end.utcoffset() is None:
        raise ValueError("window_end must be timezone-aware")
    if window_end <= window_start:
        raise ValueError("window_end must be after window_start")
    if window_end - window_start > timedelta(days=14):
        raise ValueError("Historical windows must be 14 days or shorter")
    if page_size < 1 or page_size > 1000:
        raise ValueError("page_size must be between 1 and 1000")
    if max_pages < 1:
        raise ValueError("max_pages must be positive")

    source_system = "jobdiva"
    run_id = str(uuid4())
    await store.start_run(
        run_id=run_id,
        tenant_id=tenant_id,
        source_system=source_system,
        stream=stream,
        mode="backfill",
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
            if source_ids_sink is not None:
                source_ids_sink.update(source_id(stream, record) for record in records)

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
            raise RuntimeError("JobDiva backfill pagination reached the configured safety ceiling")

        # Historical backfill deliberately records success without advancing
        # the live delta checkpoint.
        await store.complete_backfill_run(
            run_id=run_id,
            tenant_id=tenant_id,
            stream=stream,
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


def backfill_windows(start: datetime, end: datetime, *, max_window: timedelta = timedelta(days=14)):
    """Yield bounded, non-overlapping historical windows."""
    if start.tzinfo is None or start.utcoffset() is None or end.tzinfo is None or end.utcoffset() is None:
        raise ValueError("Backfill boundaries must be timezone-aware")
    if end <= start:
        raise ValueError("Backfill end must be after start")
    if max_window <= timedelta(0) or max_window > timedelta(days=14):
        raise ValueError("max_window must be greater than zero and no more than 14 days")
    cursor = start
    while cursor < end:
        window_end = min(cursor + max_window, end)
        yield cursor, window_end
        cursor = window_end



async def run_historical_backfill(
    client: DeltaClient,
    store: SyncStore,
    *,
    tenant_id: str,
    stream: SyncStream,
    start: datetime,
    end: datetime,
    max_window: timedelta = timedelta(days=14),
    page_size: int = 100,
    max_pages: int = 1000,
    source_ids_sink: set[str] | None = None,
) -> list[SyncRunSummary]:
    """Run only incomplete historical windows in chronological order."""
    completed: list[SyncRunSummary] = []
    for window_start, window_end in backfill_windows(start, end, max_window=max_window):
        already_done = await store.backfill_window_succeeded(
            tenant_id=tenant_id,
            source_system="jobdiva",
            stream=stream,
            window_start=window_start,
            window_end=window_end,
        )
        if already_done:
            continue
        completed.append(await run_backfill_window(
            client,
            store,
            tenant_id=tenant_id,
            stream=stream,
            window_start=window_start,
            window_end=window_end,
            page_size=page_size,
            max_pages=max_pages,
            source_ids_sink=source_ids_sink,
        ))
    return completed
