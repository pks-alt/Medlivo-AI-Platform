from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app
from app.routes import career as career_routes
from app.routes import application as application_routes
from app.schemas.career import PublicJobDetail, PublicJobListItem, PublicJobPage, PublicJobSection
from app.schemas.application import CareerApplicationReceipt


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


def test_public_job_application_returns_safe_receipt(monkeypatch):
    async def fake_submit(value):
        assert value.job_id == JOB_ID
        assert value.email == "clinician@example.com"
        return CareerApplicationReceipt(
            application_id=UUID("00000000-0000-0000-0000-000000000902"),
            job_id=JOB_ID,
            status="received",
            candidate_status="matched_existing_candidate",
            ownership_status="owned",
            recruiter_assigned=True,
        )

    monkeypatch.setattr(application_routes, "submit_career_application", fake_submit)
    with TestClient(app) as client:
        response = client.post("/api/v1/careers/applications", json={
            "job_id": str(JOB_ID),
            "name": "Synthetic Clinician",
            "email": "Clinician@Example.com",
            "phone": "555-0100",
            "profession": "Physical Therapist",
            "specialty": "Physical Therapy",
            "preferred_location": "CA",
            "availability": "2026-11-15",
            "resume_url": "https://example.com/resume.pdf",
            "consent_to_contact": True,
        })
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "received"
    assert body["recruiter_assigned"] is True
    assert "email" not in body
    assert response.headers["cache-control"] == "no-store"


def test_job_application_requires_contact_consent(monkeypatch):
    async def should_not_run(value):
        raise AssertionError("submit should not run")

    monkeypatch.setattr(application_routes, "submit_career_application", should_not_run)
    with TestClient(app) as client:
        response = client.post("/api/v1/careers/applications", json={
            "job_id": str(JOB_ID),
            "name": "Synthetic Clinician",
            "email": "clinician@example.com",
            "consent_to_contact": False,
        })
    assert response.status_code == 422


def test_job_application_for_unavailable_job_returns_404(monkeypatch):
    async def missing(value):
        raise KeyError(value.job_id)

    monkeypatch.setattr(application_routes, "submit_career_application", missing)
    with TestClient(app) as client:
        response = client.post("/api/v1/careers/applications", json={
            "job_id": str(JOB_ID),
            "name": "Synthetic Clinician",
            "email": "clinician@example.com",
            "consent_to_contact": True,
        })
    assert response.status_code == 404
