from datetime import date

from sqlalchemy import insert, update
from fastapi.testclient import TestClient

from workspace_api import tables as t
from workspace_api.app import build_app
from workspace_api.store import now, WorkspaceStore
from workspace_api.submission_ai import SubmissionAIResult
from workspace_api.submission_artifacts import GeneratedPacket


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


def test_recruiter_can_review_narrative_then_finalize_ready_package(client, headers, seeded):
    seed_rehab_submission_ready(seeded)
    client.post(
        "/api/v1/team/submission-studio/bootstrap-templates",
        headers={**headers("admin-a"), "Idempotency-Key": idn(9940)},
        json={"activate": True},
    )
    prepared = client.post(
        f"/api/v1/team/submission-studio/jobs/{idn(200)}/candidates/{idn(300)}/prepare",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9941)},
        json={},
    )
    assert prepared.status_code == 200
    body = prepared.json()
    narrative = next(x for x in body["items"] if x["requirement_key"] == "candidate_summary")

    reviewed = client.post(
        f"/api/v1/team/submission-studio/packages/{body['id']}/items/{narrative['id']}/review",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9942)},
        json={
            "decision": "approved",
            "recruiter_note": "Reviewed against source-supported candidate facts.",
            "resolved_value": {
                "text": "Physical Therapist with verified NY licensure and relevant rehabilitation experience."
            },
        },
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["readiness_status"] == "ready"

    finalized = client.post(
        f"/api/v1/team/submission-studio/packages/{body['id']}/finalize",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9943)},
        json={"confirmation": "reviewed_and_ready"},
    )
    assert finalized.status_code == 200
    assert finalized.json()["status"] == "finalized"
    assert finalized.json()["finalized_by"] == idn(10)


def test_missing_required_document_cannot_be_manually_overridden(client, headers, seeded):
    seed_rehab_submission_ready(seeded)
    with seeded.begin() as conn:
        conn.execute(update(t.jobs).where(t.jobs.c.id == idn(200)).values(
            division="Nursing & Allied", profession="Registered Nurse", specialty="ICU"
        ))
        conn.execute(update(t.candidates).where(t.candidates.c.id == idn(300)).values(
            profession="Registered Nurse", specialty="ICU"
        ))
    client.post(
        "/api/v1/team/submission-studio/bootstrap-templates",
        headers={**headers("admin-a"), "Idempotency-Key": idn(9950)},
        json={"activate": True},
    )
    prepared = client.post(
        f"/api/v1/team/submission-studio/jobs/{idn(200)}/candidates/{idn(300)}/prepare",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9951)},
        json={},
    )
    assert prepared.status_code == 200
    body = prepared.json()
    skills = next(x for x in body["items"] if x["requirement_key"] == "skills_checklist")
    bypass = client.post(
        f"/api/v1/team/submission-studio/packages/{body['id']}/items/{skills['id']}/review",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9952)},
        json={
            "decision": "approved",
            "recruiter_note": "Recruiter says checklist is available.",
            "resolved_value": {"value": "available"},
        },
    )
    assert bypass.status_code == 422
    assert "required document" in bypass.json()["detail"].lower()


def test_customer_program_template_versions_and_outranks_division_default(client, headers, seeded):
    seed_rehab_submission_ready(seeded)
    with seeded.begin() as conn:
        conn.execute(insert(t.customers).values(
            id=idn(1960), tenant_id=idn(1), name="Synthetic MSP", status="active",
            metadata={}, created_at=now(), updated_at=now()
        ))
        conn.execute(update(t.jobs).where(t.jobs.c.id == idn(200)).values(
            customer_id=idn(1960)
        ))
    boot = client.post(
        "/api/v1/team/submission-studio/bootstrap-templates",
        headers={**headers("admin-a"), "Idempotency-Key": idn(9960)},
        json={"activate": True},
    )
    assert boot.status_code == 200
    parent = next(x for x in boot.json()["created"] if x["division"] == "Rehabilitation")

    template_payload = {
        "name": "Synthetic MSP Rehab Program",
        "division": "Rehabilitation",
        "customer_id": idn(1960),
        "program_name": "Program A",
        "profession": None,
        "specialty": None,
        "template_scope": "program",
        "parent_template_id": parent["template_id"],
        "activate": True,
        "resume_format_profile": {"style": "medlivo_standard"},
        "output_profile": {"combined_pdf": True},
        "ai_policy": {"candidate_summary": True},
        "requirements": [
            {
                "requirement_key": "professional_references",
                "label": "Two Professional References",
                "requirement_type": "reference",
                "category": "references",
                "lifecycle_stage": "submission",
                "sensitivity": "standard",
                "fulfillment_strategy": "source_only",
                "required": True,
                "source_preference": [],
                "validation_rule": {"min_count": 2},
                "output_rule": {},
                "display_order": 10,
            }
        ],
    }
    created = client.post(
        "/api/v1/team/submission-studio/templates",
        headers={**headers("admin-a"), "Idempotency-Key": idn(9961)},
        json=template_payload,
    )
    assert created.status_code == 200
    assert created.json()["version"] == 1

    created_v2 = client.post(
        "/api/v1/team/submission-studio/templates",
        headers={**headers("admin-a"), "Idempotency-Key": idn(9962)},
        json={**template_payload, "name": "Synthetic MSP Rehab Program v2"},
    )
    assert created_v2.status_code == 200
    assert created_v2.json()["version"] == 2

    prepared = client.post(
        f"/api/v1/team/submission-studio/jobs/{idn(200)}/candidates/{idn(300)}/prepare",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9963)},
        json={"program_name": "Program A"},
    )
    assert prepared.status_code == 200
    body = prepared.json()
    assert body["template"]["name"] == "Synthetic MSP Rehab Program v2"
    keys = {x["requirement_key"] for x in body["items"]}
    assert {"resume", "active_license", "candidate_summary", "professional_references"} <= keys
    assert body["readiness_status"] == "missing_required"


class FakeSubmissionAI:
    def compose(self, context):
        assert "source" in context
        assert "ssn" not in context["source"]
        return SubmissionAIResult(
            candidate_summary="Verified PT candidate with relevant rehabilitation experience and active New York licensure.",
            resume_markdown="# Synthetic Candidate One, PT\n\n## Experience\nSource-grounded rehabilitation experience.",
            claims=[
                {"text": "Active New York licensure", "source_keys": ["license." + idn(1902)]},
                {"text": "Physical Therapist", "source_keys": ["candidate.profession"]},
            ],
            warnings=["Review employment dates before final customer submission."],
            provider="fake_vertex",
            model="fake-model",
        )


def test_ai_composer_fails_closed_when_not_configured(client, headers, seeded):
    seed_rehab_submission_ready(seeded)
    client.post(
        "/api/v1/team/submission-studio/bootstrap-templates",
        headers={**headers("admin-a"), "Idempotency-Key": idn(9970)},
        json={"activate": True},
    )
    prepared = client.post(
        f"/api/v1/team/submission-studio/jobs/{idn(200)}/candidates/{idn(300)}/prepare",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9971)},
        json={},
    )
    assert prepared.status_code == 200
    response = client.post(
        f"/api/v1/team/submission-studio/packages/{prepared.json()['id']}/compose-ai",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9972)},
        json={},
    )
    assert response.status_code == 503


def test_ai_composer_creates_source_grounded_draft_but_does_not_auto_approve(
    seeded, verifier, headers
):
    seed_rehab_submission_ready(seeded)
    ai_client = TestClient(build_app(WorkspaceStore(seeded, submission_ai=FakeSubmissionAI()), verifier))
    boot = ai_client.post(
        "/api/v1/team/submission-studio/bootstrap-templates",
        headers={**headers("admin-a"), "Idempotency-Key": idn(9980)},
        json={"activate": True},
    )
    assert boot.status_code == 200
    prepared = ai_client.post(
        f"/api/v1/team/submission-studio/jobs/{idn(200)}/candidates/{idn(300)}/prepare",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9981)},
        json={},
    )
    assert prepared.status_code == 200

    drafted = ai_client.post(
        f"/api/v1/team/submission-studio/packages/{prepared.json()['id']}/compose-ai",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9982)},
        json={},
    )
    assert drafted.status_code == 200
    body = drafted.json()
    assert body["ai_summary"]["status"] == "draft_ready"
    assert body["ai_summary"]["provider"] == "fake_vertex"
    assert body["ai_summary"]["model"] == "fake-model"
    assert body["readiness_status"] == "needs_review"
    summary_item = next(x for x in body["items"] if x["requirement_key"] == "candidate_summary")
    assert summary_item["status"] == "needs_review"
    assert summary_item["resolved_value"]["ai_generated"] is True
    assert "Verified PT candidate" in summary_item["resolved_value"]["text"]
    resume_item = next(x for x in body["items"] if x["requirement_key"] == "resume")
    assert "ai_resume_markdown" in resume_item["resolved_value"]

    finalized = ai_client.post(
        f"/api/v1/team/submission-studio/packages/{body['id']}/finalize",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9983)},
        json={"confirmation": "reviewed_and_ready"},
    )
    assert finalized.status_code == 422


class FakePacketGenerator:
    def __init__(self):
        self.contexts = []

    def generate(self, context):
        self.contexts.append(context)
        return GeneratedPacket(
            content=b"PKfake-submission-package",
            filename="Synthetic_Candidate_PT_Submission_v1.zip",
            manifest={"candidate": context["candidate"]["canonical_name"]},
        )


def _prepare_review_finalize(client, headers, seeded, key_base):
    seed_rehab_submission_ready(seeded)
    client.post(
        "/api/v1/team/submission-studio/bootstrap-templates",
        headers={**headers("admin-a"), "Idempotency-Key": idn(key_base)},
        json={"activate": True},
    )
    prepared = client.post(
        f"/api/v1/team/submission-studio/jobs/{idn(200)}/candidates/{idn(300)}/prepare",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(key_base + 1)},
        json={},
    )
    assert prepared.status_code == 200
    body = prepared.json()
    narrative = next(x for x in body["items"] if x["requirement_key"] == "candidate_summary")
    reviewed = client.post(
        f"/api/v1/team/submission-studio/packages/{body['id']}/items/{narrative['id']}/review",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(key_base + 2)},
        json={
            "decision": "approved",
            "recruiter_note": "Reviewed against verified source facts.",
            "resolved_value": {"text": "Verified Physical Therapist with active New York licensure."},
        },
    )
    assert reviewed.status_code == 200
    finalized = client.post(
        f"/api/v1/team/submission-studio/packages/{body['id']}/finalize",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(key_base + 3)},
        json={"confirmation": "reviewed_and_ready"},
    )
    assert finalized.status_code == 200
    return finalized.json()


def test_submission_download_fails_closed_when_generator_not_configured(client, headers, seeded):
    package = _prepare_review_finalize(client, headers, seeded, 9990)
    response = client.get(
        f"/api/v1/team/submission-studio/packages/{package['id']}/download",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 503


def test_finalized_submission_download_is_recruiter_scoped_and_binary(seeded, verifier, headers):
    generator = FakePacketGenerator()
    download_client = TestClient(build_app(
        WorkspaceStore(seeded, submission_packet_generator=generator), verifier
    ))
    package = _prepare_review_finalize(download_client, headers, seeded, 10010)

    response = download_client.get(
        f"/api/v1/team/submission-studio/packages/{package['id']}/download",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "Synthetic_Candidate_PT_Submission_v1.zip" in response.headers["content-disposition"]
    assert response.content == b"PKfake-submission-package"
    assert generator.contexts[0]["candidate"]["canonical_name"] == "Synthetic Candidate One"

    other = download_client.get(
        f"/api/v1/team/submission-studio/packages/{package['id']}/download",
        headers=headers("recruiter-b"),
    )
    assert other.status_code == 404


def test_draft_submission_cannot_be_downloaded(seeded, verifier, headers):
    generator = FakePacketGenerator()
    download_client = TestClient(build_app(
        WorkspaceStore(seeded, submission_packet_generator=generator), verifier
    ))
    seed_rehab_submission_ready(seeded)
    download_client.post(
        "/api/v1/team/submission-studio/bootstrap-templates",
        headers={**headers("admin-a"), "Idempotency-Key": idn(10020)},
        json={"activate": True},
    )
    prepared = download_client.post(
        f"/api/v1/team/submission-studio/jobs/{idn(200)}/candidates/{idn(300)}/prepare",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(10021)},
        json={},
    )
    assert prepared.status_code == 200
    response = download_client.get(
        f"/api/v1/team/submission-studio/packages/{prepared.json()['id']}/download",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 422
    assert generator.contexts == []
