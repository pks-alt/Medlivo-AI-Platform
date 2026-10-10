from datetime import date

from sqlalchemy import insert, update

from workspace_api import tables as t
from workspace_api.store import now


def idn(n):
    return f"00000000-0000-0000-0000-{n:012d}"


def seed_rehab_submission_ready(seeded):
    with seeded.begin() as conn:
        conn.execute(update(t.jobs).where(t.jobs.c.id == idn(200)).values(
            division="Rehabilitation", profession="Physical Therapist",
            specialty="PT", state="NY", owner_user_id=idn(10)
        ))
        conn.execute(update(t.candidates).where(t.candidates.c.id == idn(300)).values(
            profession="Physical Therapist", specialty="PT", state="NY",
            canonical_profile={"years_experience": 6, "settings": ["SNF", "Outpatient"]}
        ))
        conn.execute(insert(t.matches).values(
            id=idn(1900), tenant_id=idn(1), job_id=idn(200), candidate_id=idn(300),
            overall_score=9.2, status="active", rules_version="test",
            explanation={"strengths": ["PT", "NY"]}, created_at=now(), updated_at=now()
        ))
        conn.execute(insert(t.resume_versions).values(
            id=idn(1901), tenant_id=idn(1), candidate_id=idn(300),
            source_record_id=None, source_resume_id="resume-300", storage_uri="gs://test/resume.pdf",
            text_content="Synthetic PT resume", parsed_payload={}, is_primary=True,
            resume_date=date(2026, 10, 1), created_at=now(), updated_at=now()
        ))
        conn.execute(insert(t.candidate_licenses).values(
            id=idn(1902), tenant_id=idn(1), candidate_id=idn(300),
            license_type="PT", state="NY", license_number="046769", status="active",
            issued_at=None, expires_at=date(2029, 2, 28),
            verification_status="verified", verified_at=now(),
            verification_source="primary_source", source_system="test",
            source_reference="license-300", raw_payload={}, created_at=now(), updated_at=now()
        ))


def test_admin_bootstraps_cross_division_submission_defaults(client, headers):
    response = client.post(
        "/api/v1/team/submission-studio/bootstrap-templates",
        headers={**headers("admin-a"), "Idempotency-Key": idn(9900)},
        json={"activate": True},
    )
    assert response.status_code == 200
    created = response.json()["created"]
    assert {x["division"] for x in created} == {
        "Rehabilitation", "Nursing & Allied", "Locum Tenens"
    }

    second = client.post(
        "/api/v1/team/submission-studio/bootstrap-templates",
        headers={**headers("admin-a"), "Idempotency-Key": idn(9901)},
        json={"activate": True},
    )
    assert second.status_code == 200
    assert second.json()["created"] == []
    assert len(second.json()["existing"]) == 3


def test_recruiter_cannot_bootstrap_submission_templates(client, headers):
    response = client.post(
        "/api/v1/team/submission-studio/bootstrap-templates",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9902)},
        json={"activate": True},
    )
    assert response.status_code == 403


def test_rehab_package_reuses_resume_and_verified_license_but_requires_narrative_review(
    client, headers, seeded
):
    seed_rehab_submission_ready(seeded)
    boot = client.post(
        "/api/v1/team/submission-studio/bootstrap-templates",
        headers={**headers("admin-a"), "Idempotency-Key": idn(9910)},
        json={"activate": True},
    )
    assert boot.status_code == 200

    response = client.post(
        f"/api/v1/team/submission-studio/jobs/{idn(200)}/candidates/{idn(300)}/prepare",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9911)},
        json={"program_name": None},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["template"]["division"] == "Rehabilitation"
    assert body["readiness_status"] == "needs_review"
    assert float(body["readiness_score"]) > 60
    by_key = {x["requirement_key"]: x for x in body["items"]}
    assert by_key["resume"]["status"] == "matched"
    assert by_key["active_license"]["status"] == "matched"
    assert by_key["candidate_summary"]["status"] == "needs_review"
    assert body["ai_summary"]["status"] == "model_pending"


def test_missing_required_item_blocks_submission_readiness(client, headers, seeded):
    seed_rehab_submission_ready(seeded)
    with seeded.begin() as conn:
        conn.execute(update(t.jobs).where(t.jobs.c.id == idn(200)).values(
            division="Nursing & Allied", profession="Registered Nurse", specialty="ICU"
        ))
        conn.execute(update(t.candidates).where(t.candidates.c.id == idn(300)).values(
            profession="Registered Nurse", specialty="ICU"
        ))
    boot = client.post(
        "/api/v1/team/submission-studio/bootstrap-templates",
        headers={**headers("admin-a"), "Idempotency-Key": idn(9920)},
        json={"activate": True},
    )
    assert boot.status_code == 200

    response = client.post(
        f"/api/v1/team/submission-studio/jobs/{idn(200)}/candidates/{idn(300)}/prepare",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9921)},
        json={},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["readiness_status"] == "missing_required"
    skills = next(x for x in body["items"] if x["requirement_key"] == "skills_checklist")
    assert skills["status"] == "missing"
    assert any(
        x["code"] == "required_item_missing" and x["field_key"] == "skills_checklist"
        for x in body["validations"]
    )


def test_submission_package_versions_are_immutable_and_history_is_recruiter_scoped(
    client, headers, seeded
):
    seed_rehab_submission_ready(seeded)
    client.post(
        "/api/v1/team/submission-studio/bootstrap-templates",
        headers={**headers("admin-a"), "Idempotency-Key": idn(9930)},
        json={"activate": True},
    )
    first = client.post(
        f"/api/v1/team/submission-studio/jobs/{idn(200)}/candidates/{idn(300)}/prepare",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9931)},
        json={},
    )
    second = client.post(
        f"/api/v1/team/submission-studio/jobs/{idn(200)}/candidates/{idn(300)}/prepare",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9932)},
        json={},
    )
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["version"] == 1
    assert second.json()["version"] == 2

    history = client.get(
        f"/api/v1/team/submission-studio/packages?job_id={idn(200)}&candidate_id={idn(300)}",
        headers=headers("recruiter-a"),
    )
    assert history.status_code == 200
    assert [x["version"] for x in history.json()["items"]] == [2, 1]
    assert history.json()["items"][1]["status"] == "superseded"

    other = client.get(
        "/api/v1/team/submission-studio/packages",
        headers=headers("recruiter-b"),
    )
    assert other.status_code == 200
    assert other.json()["items"] == []
