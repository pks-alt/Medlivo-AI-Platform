from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.repositories.integration import classify_sync_status
from app.routes import integration as integration_routes
from app.schemas.integration import JobDivaSyncHealth, SyncStreamHealth


def test_health_classification_prioritizes_errors():
    watermark = datetime(2026, 10, 8, tzinfo=timezone.utc)
    assert classify_sync_status(
        watermark=watermark,
        last_error_code="RuntimeError",
        last_run_status="failed",
        freshness_minutes=1,
        stale_after_minutes=30,
    ) == "error"


def test_health_classification_marks_never_synced_and_stale():
    assert classify_sync_status(
        watermark=None,
        last_error_code=None,
        last_run_status=None,
        freshness_minutes=None,
        stale_after_minutes=30,
    ) == "never_synced"
    assert classify_sync_status(
        watermark=datetime(2026, 10, 8, tzinfo=timezone.utc),
        last_error_code=None,
        last_run_status="succeeded",
        freshness_minutes=31,
        stale_after_minutes=30,
    ) == "stale"


def test_health_classification_marks_fresh_success_healthy():
    assert classify_sync_status(
        watermark=datetime(2026, 10, 8, tzinfo=timezone.utc),
        last_error_code=None,
        last_run_status="succeeded",
        freshness_minutes=5,
        stale_after_minutes=30,
    ) == "healthy"


def test_jobdiva_health_endpoint_returns_operational_metadata_only(monkeypatch):
    async def fake_health(*, stale_after_minutes):
        assert stale_after_minutes == 45
        return JobDivaSyncHealth(
            generated_at=datetime(2026, 10, 8, 1, 30, tzinfo=timezone.utc),
            streams=[
                SyncStreamHealth(
                    tenant_slug="medlivo",
                    source_system="jobdiva",
                    stream="jobs",
                    status="healthy",
                    watermark=datetime(2026, 10, 8, 1, 20, tzinfo=timezone.utc),
                    last_success_at=datetime(2026, 10, 8, 1, 21, tzinfo=timezone.utc),
                    last_run_status="succeeded",
                    freshness_minutes=10,
                    latest_records_seen=25,
                    latest_records_upserted=25,
                )
            ],
        )

    monkeypatch.setattr(integration_routes, "get_jobdiva_sync_health", fake_health)
    with TestClient(app) as client:
        response = client.get("/api/v1/integrations/jobdiva/health?stale_after_minutes=45")

    assert response.status_code == 200
    body = response.json()
    assert body["streams"][0]["status"] == "healthy"
    assert body["streams"][0]["latest_records_seen"] == 25
    assert "raw_payload" not in response.text


def test_jobdiva_health_rejects_unreasonable_staleness_threshold():
    with TestClient(app) as client:
        response = client.get("/api/v1/integrations/jobdiva/health?stale_after_minutes=1")
    assert response.status_code == 422
