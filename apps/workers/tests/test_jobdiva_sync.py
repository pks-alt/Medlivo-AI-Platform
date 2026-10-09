from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from jobdiva_sync import SyncStream, backfill_windows, run_backfill_window, run_delta_sync, run_historical_backfill


class FakeClient:
    def __init__(self, pages, fail_page=None):
        self.pages = pages
        self.fail_page = fail_page
        self.calls = []

    async def updated_jobs(self, **kwargs):
        page = kwargs["page_number"]
        self.calls.append(("jobs", page, kwargs["from_date"], kwargs["to_date"]))
        if page == self.fail_page:
            raise RuntimeError("synthetic page failure")
        return self.pages.get(page, [])

    async def updated_candidates(self, **kwargs):
        page = kwargs["page_number"]
        self.calls.append(("candidates", page, kwargs["from_date"], kwargs["to_date"]))
        if page == self.fail_page:
            raise RuntimeError("synthetic page failure")
        return self.pages.get(page, [])


class FakeStore:
    def __init__(self, watermark=None):
        self.watermark = watermark
        self.runs = {}
        self.records = {}
        self.checkpoint_updates = 0
        self.completed_backfills = set()

    async def checkpoint(self, tenant_id, source_system, stream):
        return self.watermark

    async def start_run(self, **kwargs):
        self.runs[kwargs["run_id"]] = {"status": "running", **kwargs}

    async def upsert_page(self, *, tenant_id, source_system, stream, records):
        ids = {}
        key_names = ("JOBID", "jobId", "id") if stream == SyncStream.JOBS else ("CANDIDATEID", "candidateId", "id")
        for record in records:
            ident = next(str(record[k]) for k in key_names if k in record)
            ids[ident] = record
        self.records.update(ids)
        return len(ids)

    async def succeed_run(self, **kwargs):
        self.runs[kwargs["run_id"]].update({"status": "succeeded", **kwargs})
        self.watermark = kwargs["window_end"]
        self.checkpoint_updates += 1

    async def fail_run(self, **kwargs):
        self.runs[kwargs["run_id"]].update({"status": "failed", **kwargs})

    async def complete_backfill_run(self, **kwargs):
        run = self.runs[kwargs["run_id"]]
        run.update({"status": "succeeded", **kwargs})
        self.completed_backfills.add((run["stream"], run["window_start"], run["window_end"]))

    async def backfill_window_succeeded(self, *, tenant_id, source_system, stream, window_start, window_end):
        return (stream, window_start, window_end) in self.completed_backfills


NOW = datetime(2026, 10, 8, 1, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_success_advances_checkpoint_only_after_full_window():
    store = FakeStore()
    client = FakeClient({
        1: [{"JOBID": 101}, {"JOBID": 102}],
        2: [{"JOBID": 103}],
    })

    result = await run_delta_sync(
        client,
        store,
        tenant_id="tenant-1",
        stream=SyncStream.JOBS,
        now=NOW,
        page_size=2,
    )

    assert result.pages_processed == 2
    assert result.records_seen == 3
    assert result.records_upserted == 3
    assert set(store.records) == {"101", "102", "103"}
    assert store.watermark == NOW - timedelta(minutes=2)
    assert store.checkpoint_updates == 1


@pytest.mark.asyncio
async def test_partial_failure_does_not_advance_checkpoint():
    old = NOW - timedelta(days=1)
    store = FakeStore(watermark=old)
    client = FakeClient({1: [{"CANDIDATEID": 201}, {"CANDIDATEID": 202}]}, fail_page=2)

    with pytest.raises(RuntimeError, match="synthetic page failure"):
        await run_delta_sync(
            client,
            store,
            tenant_id="tenant-1",
            stream=SyncStream.CANDIDATES,
            now=NOW,
            page_size=2,
        )

    assert store.watermark == old
    assert store.checkpoint_updates == 0
    assert set(store.records) == {"201", "202"}
    run = next(iter(store.runs.values()))
    assert run["status"] == "failed"


@pytest.mark.asyncio
async def test_replay_is_idempotent_by_source_id():
    store = FakeStore(watermark=NOW - timedelta(hours=2))
    first = FakeClient({1: [{"JOBID": 101, "TITLE": "Old"}, {"JOBID": 102}]})
    second = FakeClient({1: [{"JOBID": 101, "TITLE": "Updated"}, {"JOBID": 102}]})

    await run_delta_sync(first, store, tenant_id="tenant-1", stream=SyncStream.JOBS, now=NOW, page_size=100)

    replay_now = NOW + timedelta(minutes=10)
    await run_delta_sync(second, store, tenant_id="tenant-1", stream=SyncStream.JOBS, now=replay_now, page_size=100)

    assert len(store.records) == 2
    assert store.records["101"]["TITLE"] == "Updated"


@pytest.mark.asyncio
async def test_existing_checkpoint_uses_overlap_window():
    old = NOW - timedelta(hours=1)
    store = FakeStore(watermark=old)
    client = FakeClient({})

    await run_delta_sync(
        client,
        store,
        tenant_id="tenant-1",
        stream=SyncStream.JOBS,
        now=NOW,
        overlap=timedelta(minutes=5),
    )

    _, _, from_date, _ = client.calls[0]
    assert from_date == old - timedelta(minutes=5)


@pytest.mark.asyncio
async def test_missing_source_id_fails_window_and_preserves_checkpoint():
    old = NOW - timedelta(hours=1)
    store = FakeStore(watermark=old)
    client = FakeClient({1: [{"TITLE": "Missing ID"}]})

    with pytest.raises(ValueError, match="missing a source ID"):
        await run_delta_sync(
            client,
            store,
            tenant_id="tenant-1",
            stream=SyncStream.JOBS,
            now=NOW,
            page_size=100,
        )

    assert store.watermark == old
    assert next(iter(store.runs.values()))["status"] == "failed"


def test_backfill_windows_are_bounded_and_non_overlapping():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 2, 1, tzinfo=timezone.utc)
    windows = list(backfill_windows(start, end))
    assert len(windows) == 3
    assert windows[0] == (start, datetime(2026, 1, 15, tzinfo=timezone.utc))
    assert windows[1][0] == windows[0][1]
    assert windows[2][1] == end
    assert all((b - a) <= timedelta(days=14) for a, b in windows)


@pytest.mark.asyncio
async def test_backfill_does_not_move_live_delta_checkpoint():
    old = NOW - timedelta(hours=1)
    store = FakeStore(watermark=old)
    client = FakeClient({1: [{"JOBID": 301}]})

    result = await run_backfill_window(
        client,
        store,
        tenant_id="tenant-1",
        stream=SyncStream.JOBS,
        window_start=NOW - timedelta(days=14),
        window_end=NOW - timedelta(days=7),
        page_size=100,
    )

    assert result.records_seen == 1
    assert store.watermark == old
    assert store.checkpoint_updates == 0
    run = next(iter(store.runs.values()))
    assert run["mode"] == "backfill"
    assert run["status"] == "succeeded"


@pytest.mark.asyncio
async def test_backfill_window_larger_than_fourteen_days_is_rejected():
    store = FakeStore()
    client = FakeClient({})
    with pytest.raises(ValueError, match="14 days"):
        await run_backfill_window(
            client,
            store,
            tenant_id="tenant-1",
            stream=SyncStream.CANDIDATES,
            window_start=NOW - timedelta(days=15),
            window_end=NOW,
        )


@pytest.mark.asyncio
async def test_historical_backfill_skips_windows_already_completed():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 29, tzinfo=timezone.utc)
    store = FakeStore()
    first_window = (SyncStream.JOBS, start, start + timedelta(days=14))
    store.completed_backfills.add(first_window)
    client = FakeClient({1: []})

    completed = await run_historical_backfill(
        client,
        store,
        tenant_id="tenant-1",
        stream=SyncStream.JOBS,
        start=start,
        end=end,
    )

    assert len(completed) == 1
    assert client.calls[0][2] == start + timedelta(days=14)
    assert client.calls[0][3] == end


@pytest.mark.asyncio
async def test_backfill_can_capture_exact_source_ids_for_targeted_promotion():
    store = FakeStore()
    sink = set()
    client = FakeClient({
        1: [{"JOBID": 501}, {"JOBID": 502}],
        2: [{"JOBID": 503}],
    })
    await run_backfill_window(
        client,
        store,
        tenant_id="tenant-1",
        stream=SyncStream.JOBS,
        window_start=NOW - timedelta(days=14),
        window_end=NOW,
        page_size=2,
        source_ids_sink=sink,
    )
    assert sink == {"501", "502", "503"}
