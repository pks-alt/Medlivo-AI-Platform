from decimal import Decimal

from sqlalchemy import insert, select

from margin_engine import GuidelineBands, seed_assumptions
from workspace_api import tables as t
from workspace_api.store import now


def idn(n):
    return f"00000000-0000-0000-0000-{n:012d}"


def configure_1099_guidelines(seeded):
    assumptions = seed_assumptions("locums_national_1099").model_copy(
        update={
            "guideline_bands": GuidelineBands(
                recruiter_guideline_min_margin=Decimal("0.20"),
                delivery_manager_discussion_min_margin=Decimal("0.10"),
                legacy_workbook_floor=Decimal("0.10"),
            )
        }
    )
    with seeded.begin() as conn:
        conn.execute(insert(t.cost_assumption_sets).values(
            id=idn(1200),
            tenant_id=idn(1),
            profile=assumptions.profile,
            version=assumptions.version,
            assumption_payload=assumptions.model_dump(mode="json"),
            status="active",
            effective_from=now(),
            effective_to=None,
            created_by=idn(10),
            created_at=now(),
        ))


def margin_payload(gross_billing, contractor_pay, recruiter_user_id=None):
    return {
        "job_id": idn(200),
        "candidate_id": idn(300),
        "recruiter_user_id": recruiter_user_id or idn(10),
        "profile": "locums_national_1099",
        "division": "locum_tenens",
        "customer_type": "direct",
        "contract_type": "new_contract",
        "candidate_source": "internal_database",
        "assignment_weeks_equivalent": 13,
        "gross_client_billing_per_week": gross_billing,
        "contractor_compensation_per_week": contractor_pay,
        "actual_worked_hours_per_week": 40,
        "shifts_per_week": 5,
    }


def test_recruiter_finalizes_within_guideline_without_manager_approval(client, headers, seeded):
    configure_1099_guidelines(seeded)
    created = client.post(
        "/api/v1/team/margin/snapshots",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9001)},
        json=margin_payload(10000, 6000),
    )
    assert created.status_code == 201
    snapshot = created.json()
    assert snapshot["guideline_status"] == "within_guideline"
    assert snapshot["version"] == 1

    finalized = client.post(
        f"/api/v1/team/margin/snapshots/{snapshot['id']}/finalize",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9002)},
        json={"expected_version": 1},
    )
    assert finalized.status_code == 200
    assert finalized.json()["lifecycle_status"] == "finalized"
    assert finalized.json()["finalized_by"] == idn(10)


def test_out_of_guideline_rate_requires_discussion_record_not_manager_approval(client, headers, seeded):
    configure_1099_guidelines(seeded)
    created = client.post(
        "/api/v1/team/margin/snapshots",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9010)},
        json=margin_payload(8000, 6000),
    )
    snapshot = created.json()
    assert snapshot["guideline_status"] == "discuss_delivery_manager"

    premature = client.post(
        f"/api/v1/team/margin/snapshots/{snapshot['id']}/finalize",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9011)},
        json={"expected_version": 1},
    )
    assert premature.status_code == 422

    discussion = client.post(
        f"/api/v1/team/margin/snapshots/{snapshot['id']}/discussions",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9012)},
        json={
            "participant_role": "delivery_manager",
            "discussion_type": "rate_guidance",
            "notes": "Reviewed the package and commercial context with the Delivery Manager.",
        },
    )
    assert discussion.status_code == 201

    finalized = client.post(
        f"/api/v1/team/margin/snapshots/{snapshot['id']}/finalize",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9013)},
        json={"expected_version": 1},
    )
    assert finalized.status_code == 200
    assert finalized.json()["lifecycle_status"] == "finalized"


def test_leadership_flag_requires_leadership_discussion(client, headers, seeded):
    configure_1099_guidelines(seeded)
    created = client.post(
        "/api/v1/team/margin/snapshots",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9020)},
        json=margin_payload(7000, 6000),
    )
    snapshot = created.json()
    assert snapshot["guideline_status"] == "discuss_leadership"

    dm = client.post(
        f"/api/v1/team/margin/snapshots/{snapshot['id']}/discussions",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9021)},
        json={
            "participant_role": "delivery_manager",
            "discussion_type": "commercial_exception",
            "notes": "Discussed with the Delivery Manager first.",
        },
    )
    assert dm.status_code == 201

    still_blocked = client.post(
        f"/api/v1/team/margin/snapshots/{snapshot['id']}/finalize",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9022)},
        json={"expected_version": 1},
    )
    assert still_blocked.status_code == 422

    leadership = client.post(
        f"/api/v1/team/margin/snapshots/{snapshot['id']}/discussions",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9023)},
        json={
            "participant_role": "designated_leadership",
            "discussion_type": "commercial_exception",
            "notes": "Reviewed the commercial exception with designated leadership.",
        },
    )
    assert leadership.status_code == 201

    finalized = client.post(
        f"/api/v1/team/margin/snapshots/{snapshot['id']}/finalize",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9024)},
        json={"expected_version": 1},
    )
    assert finalized.status_code == 200


def test_negative_gm_creates_hard_exception_and_blocks_normal_finalization(client, headers, seeded):
    configure_1099_guidelines(seeded)
    created = client.post(
        "/api/v1/team/margin/snapshots",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9030)},
        json=margin_payload(5000, 6000),
    )
    assert created.status_code == 201
    snapshot = created.json()
    assert snapshot["guideline_status"] == "negative_gm"
    assert snapshot["lifecycle_status"] == "hard_exception_required"

    blocked = client.post(
        f"/api/v1/team/margin/snapshots/{snapshot['id']}/finalize",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9031)},
        json={"expected_version": 1},
    )
    assert blocked.status_code == 422

    with seeded.begin() as conn:
        request = conn.execute(select(t.approval_requests).where(
            t.approval_requests.c.tenant_id == idn(1),
            t.approval_requests.c.object_type == "margin_snapshot",
            t.approval_requests.c.object_id == snapshot["id"],
        )).mappings().one()
    assert request["approval_type"] == "negative_margin_exception"
    assert request["required_authority"] == "executive"
    assert request["status"] == "pending"


def test_margin_negotiation_versions_are_immutable_and_commission_is_projected(client, headers, seeded):
    configure_1099_guidelines(seeded)
    first = client.post(
        "/api/v1/team/margin/snapshots",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9040)},
        json=margin_payload(10000, 6000),
    ).json()
    second = client.post(
        "/api/v1/team/margin/snapshots",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9041)},
        json=margin_payload(10000, 6200),
    ).json()

    assert first["version"] == 1
    assert second["version"] == 2
    assert first["id"] != second["id"]

    detail = client.get(
        f"/api/v1/team/margin/snapshots/{second['id']}",
        headers=headers("recruiter-a"),
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["commission_projection"]["status"] == "projected"
    assert float(body["commission_projection"]["projected_amount"]) > 0
    assert len(body["cost_components"]) > 0


def test_recruiter_cannot_create_rate_package_for_another_recruiter(client, headers, seeded):
    configure_1099_guidelines(seeded)
    response = client.post(
        "/api/v1/team/margin/snapshots",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9050)},
        json=margin_payload(10000, 6000, recruiter_user_id=idn(11)),
    )
    assert response.status_code == 403
