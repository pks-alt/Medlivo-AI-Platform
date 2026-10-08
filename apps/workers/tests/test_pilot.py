import os

import pytest

import pilot
from pilot import PilotLimits, limits_from_env, run_pilot_once


def test_pilot_disabled_by_default(monkeypatch):
    monkeypatch.delenv("PILOT_ENABLED", raising=False)
    assert pilot.pilot_enabled() is False


def test_pilot_limits_are_bounded(monkeypatch):
    monkeypatch.setenv("PILOT_MATCHING_LIMIT", "2001")
    with pytest.raises(ValueError, match="PILOT_MATCHING_LIMIT"):
        limits_from_env()


def test_pilot_normalizes_sqlalchemy_psycopg_url_for_direct_connection():
    url = "postgresql+psycopg://user:pass@/medlivo_team_staging?host=/cloudsql/example"
    assert (
        pilot._psycopg_database_url(url)
        == "postgresql://user:pass@/medlivo_team_staging?host=/cloudsql/example"
    )
    native = "postgresql://user:pass@localhost/db"
    assert pilot._psycopg_database_url(native) == native


@pytest.mark.asyncio
async def test_disabled_main_does_not_require_database_or_jobdiva(monkeypatch, capsys):
    monkeypatch.setenv("PILOT_ENABLED", "false")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("PILOT_TENANT_ID", raising=False)
    result = await pilot.main()
    assert result == 0
    assert "no JobDiva reads" in capsys.readouterr().out


class FakeSyncSummary:
    records_seen = 2
    records_upserted = 2
    pages_processed = 1


@pytest.mark.asyncio
async def test_pilot_sequence_is_bounded_and_ordered(monkeypatch):
    calls = []

    async def sync(client, store, **kwargs):
        calls.append(("sync", kwargs["stream"].value, kwargs["page_size"]))
        return FakeSyncSummary()

    class Promoter:
        def __init__(self, connection): pass
        async def promote_unlinked(self, **kwargs):
            calls.append(("promote", kwargs["stream"].value, kwargs["limit"]))
            return {"promoted": 1}

    class CandidateStore:
        def __init__(self, connection): pass

    class JobStore:
        def __init__(self, connection): pass

    class MatchStore:
        def __init__(self, connection): pass

    async def enrich_jobs(client, store, **kwargs):
        calls.append(("enrich_jobs", kwargs["limit"]))
        return {"enriched": 1}

    async def enrich_candidates(client, store, **kwargs):
        calls.append(("enrich_candidates", kwargs["limit"], kwargs["max_resumes"]))
        return {"enriched": 1}

    async def match(store, **kwargs):
        calls.append(("match", kwargs["limit"]))
        return {"evaluated": 1}

    monkeypatch.setattr(pilot, "run_delta_sync", sync)
    monkeypatch.setattr(pilot, "CanonicalPromoter", Promoter)
    monkeypatch.setattr(pilot, "CandidateIntelligenceStore", CandidateStore)
    monkeypatch.setattr(pilot, "JobIntelligenceStore", JobStore)
    monkeypatch.setattr(pilot, "MatchingStore", MatchStore)
    monkeypatch.setattr(pilot, "enrich_pending_jobs", enrich_jobs)
    monkeypatch.setattr(pilot, "enrich_pending_candidates", enrich_candidates)
    monkeypatch.setattr(pilot, "activate_matching", match)

    await run_pilot_once(
        connection=object(),
        client=object(),
        tenant_id="tenant-1",
        limits=PilotLimits(
            sync_page_size=50,
            promotion_limit=10,
            candidate_enrichment_limit=4,
            job_enrichment_limit=3,
            matching_limit=20,
            max_resumes=2,
        ),
    )

    assert calls == [
        ("sync", "jobs", 50),
        ("sync", "candidates", 50),
        ("promote", "jobs", 10),
        ("promote", "candidates", 10),
        ("enrich_jobs", 3),
        ("enrich_candidates", 4, 2),
        ("match", 20),
    ]


@pytest.mark.asyncio
async def test_main_authenticates_jobdiva_before_running(monkeypatch):
    monkeypatch.setenv("PILOT_ENABLED", "true")
    monkeypatch.setenv("PILOT_TENANT_ID", "tenant-1")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
    monkeypatch.setenv("JOBDIVA_LIVE_ENABLED", "true")
    monkeypatch.setenv("JOBDIVA_CLIENT_ID", "1")
    monkeypatch.setenv("JOBDIVA_USERNAME", "user@example.com")
    monkeypatch.setenv("JOBDIVA_PASSWORD", "secret")

    calls = []

    class FakeConnection:
        async def close(self):
            calls.append("close")

    class FakeAsyncConnection:
        @staticmethod
        async def connect(url):
            calls.append(("connect", url))
            return FakeConnection()

    class FakeClient:
        def __init__(self, settings):
            calls.append("client_init")
        async def __aenter__(self):
            calls.append("enter")
            return self
        async def __aexit__(self, *args):
            calls.append("exit")
        async def authenticate(self):
            calls.append("authenticate")

    async def fake_run_pilot_once(**kwargs):
        calls.append("run")
        return {}

    monkeypatch.setattr(pilot, "AsyncConnection", FakeAsyncConnection)
    monkeypatch.setattr(pilot, "JobDivaClient", FakeClient)
    monkeypatch.setattr(pilot, "run_pilot_once", fake_run_pilot_once)

    result = await pilot.main()
    assert result == 0
    assert calls.index("authenticate") < calls.index("run")
