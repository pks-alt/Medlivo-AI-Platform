from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app
from app.routes import career as career_routes
from app.schemas.career import PublicJobDetail, PublicJobListItem, PublicJobPage, PublicJobSection


JOB_ID = UUID("00000000-0000-0000-0000-000000000901")


def sample_item():
    return PublicJobListItem(
        id=JOB_ID,
        title="Physical Therapist Travel Contract - Fresno, CA",
        summary="Medlivo is seeking a Physical Therapist in Fresno, California.",
        division="rehabilitation",
        profession="Physical Therapist",
        specialty="Physical Therapy",
        city="Fresno",
        state="CA",
        care_setting="SNF",
        start_date="2026-11-29",
        end_date="2027-02-28",
        duration_weeks=13,
    )


def test_public_job_list_returns_only_public_shape(monkeypatch):
    async def fake_jobs(**kwargs):
        assert kwargs["division"] == "rehabilitation"
        assert kwargs["state"] == "CA"
        return PublicJobPage(items=[sample_item()], next_cursor=None)

    monkeypatch.setattr(career_routes, "get_public_jobs", fake_jobs)
    with TestClient(app) as client:
        response = client.get("/api/v1/careers/jobs?division=rehabilitation&state=ca")
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["title"].startswith("Physical Therapist")
    assert "bill_rate" not in body["items"][0]
    assert "source_snapshot" not in body["items"][0]
    assert response.headers["cache-control"].startswith("public")


def test_public_job_detail_does_not_expose_internal_fields(monkeypatch):
    async def fake_job(job_id):
        assert job_id == JOB_ID
        item = sample_item()
        return PublicJobDetail(
            **item.model_dump(),
            sections=[
                PublicJobSection(
                    key="overview",
                    heading="About the Opportunity",
                    content="Medlivo is seeking a Physical Therapist in Fresno, California.",
                )
            ],
            public_fields={"city": "Fresno", "state": "CA", "care_setting": "SNF"},
        )

    monkeypatch.setattr(career_routes, "get_public_job", fake_job)
    with TestClient(app) as client:
        response = client.get(f"/api/v1/careers/jobs/{JOB_ID}")
    assert response.status_code == 200
    body = response.json()
    assert body["public_fields"]["state"] == "CA"
    assert "internal_fields" not in body
    assert "bill_rate" not in body["public_fields"]


def test_unapproved_or_unknown_public_job_is_not_disclosed(monkeypatch):
    async def missing(job_id):
        raise KeyError(job_id)

    monkeypatch.setattr(career_routes, "get_public_job", missing)
    with TestClient(app) as client:
        response = client.get(f"/api/v1/careers/jobs/{JOB_ID}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_invalid_division_is_rejected_before_query(monkeypatch):
    async def should_not_run(**kwargs):
        raise AssertionError("query should not run")

    monkeypatch.setattr(career_routes, "get_public_jobs", should_not_run)
    with TestClient(app) as client:
        response = client.get("/api/v1/careers/jobs?division=unknown")
    assert response.status_code == 422
