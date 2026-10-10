from datetime import timedelta

from sqlalchemy import insert, select, update

from margin_engine import seed_assumptions
from workspace_api import tables as t
from workspace_api.store import now


def idn(n):
    return f"00000000-0000-0000-0000-{n:012d}"


def configure_negative_locums_case(seeded):
    assumptions = seed_assumptions("locums_national_1099")
    with seeded.begin() as conn:
        conn.execute(update(t.jobs).where(
            t.jobs.c.id == idn(200),
            t.jobs.c.tenant_id == idn(1),
        ).values(division="Locum Tenens", state="TX"))
        conn.execute(insert(t.cost_assumption_sets).values(
            id=idn(1500),
            tenant_id=idn(1),
            profile=assumptions.profile,
            version=assumptions.version,
            assumption_payload=assumptions.model_dump(mode="json"),
            status="active",
            effective_from=now() - timedelta(hours=1),
            effective_to=None,
            created_by=idn(13),
            created_at=now(),
        ))


def negative_package():
    return {
        "job_id": idn(200),
        "candidate_id": idn(300),
        "recruiter_user_id": idn(10),
        "worker_classification": "1099",
        "assignment_type": "contract",
        "customer_type": "direct",
        "contract_type": "new_contract",
        "candidate_source": "internal_database",
        "shifts_per_week": 5,
        "contract_weeks": 13,
        "shift_length_hours": 8,
        "client_rate_type": "hourly",
        "client_rate_amount": 125,
        "provider_rate_type": "hourly",
        "provider_rate_amount": 150,
    }


def create_negative_snapshot(client, headers, seeded, key):
    configure_negative_locums_case(seeded)
    response = client.post(
        "/api/v1/team/margin/locums-pay-package-snapshots",
        headers={**headers("recruiter-a"), "Idempotency-Key": key},
        json=negative_package(),
    )
    assert response.status_code == 201
    snapshot = response.json()
    assert snapshot["guideline_status"] == "negative_gm"
    assert snapshot["lifecycle_status"] == "hard_exception_required"
    return snapshot


def get_exception(seeded, snapshot_id):
    with seeded.begin() as conn:
        return conn.execute(select(t.approval_requests).where(
            t.approval_requests.c.tenant_id == idn(1),
            t.approval_requests.c.object_id == snapshot_id,
            t.approval_requests.c.approval_type == "negative_margin_exception",
        )).mappings().one()


def test_executive_queue_shows_pending_negative_gm_exception(client, headers, seeded):
    snapshot = create_negative_snapshot(client, headers, seeded, idn(9500))
    approval = get_exception(seeded, snapshot["id"])

    queue = client.get(
        "/api/v1/team/margin/negative-gm-exceptions",
        headers=headers("admin-a"),
    )
    assert queue.status_code == 200
    items = queue.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == approval["id"]
    assert items[0]["object_id"] == snapshot["id"]
    assert items[0]["status"] == "pending"
    assert items[0]["guideline_status"] == "negative_gm"


def test_delivery_manager_cannot_view_or_decide_negative_gm_exception(client, headers, seeded):
    snapshot = create_negative_snapshot(client, headers, seeded, idn(9510))
    approval = get_exception(seeded, snapshot["id"])

    queue = client.get(
        "/api/v1/team/margin/negative-gm-exceptions",
        headers=headers("manager-a"),
    )
    assert queue.status_code == 403

    decision = client.post(
        f"/api/v1/team/margin/negative-gm-exceptions/{approval['id']}/decision",
        headers={**headers("manager-a"), "Idempotency-Key": idn(9511)},
        json={"decision": "approved", "notes": "Manager attempted approval."},
    )
    assert decision.status_code == 403


def test_executive_approval_allows_recruiter_to_finalize(client, headers, seeded):
    snapshot = create_negative_snapshot(client, headers, seeded, idn(9520))
    approval = get_exception(seeded, snapshot["id"])

    before = client.post(
        f"/api/v1/team/margin/snapshots/{snapshot['id']}/finalize",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9521)},
        json={"expected_version": 1},
    )
    assert before.status_code == 422

    decision = client.post(
        f"/api/v1/team/margin/negative-gm-exceptions/{approval['id']}/decision",
        headers={**headers("admin-a"), "Idempotency-Key": idn(9522)},
        json={
            "decision": "approved",
            "notes": "Executive approved this documented negative-GM exception.",
        },
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "approved"
    assert decision.json()["decided_by"] == idn(13)
    assert decision.json()["snapshot_lifecycle_status"] == "exception_approved"

    finalized = client.post(
        f"/api/v1/team/margin/snapshots/{snapshot['id']}/finalize",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9523)},
        json={"expected_version": 1},
    )
    assert finalized.status_code == 200
    assert finalized.json()["lifecycle_status"] == "finalized"
    assert finalized.json()["finalized_by"] == idn(10)


def test_executive_rejection_keeps_package_blocked(client, headers, seeded):
    snapshot = create_negative_snapshot(client, headers, seeded, idn(9530))
    approval = get_exception(seeded, snapshot["id"])

    decision = client.post(
        f"/api/v1/team/margin/negative-gm-exceptions/{approval['id']}/decision",
        headers={**headers("admin-a"), "Idempotency-Key": idn(9531)},
        json={
            "decision": "rejected",
            "notes": "Commercial basis does not support a negative-GM exception.",
        },
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "rejected"
    assert decision.json()["snapshot_lifecycle_status"] == "exception_rejected"

    finalized = client.post(
        f"/api/v1/team/margin/snapshots/{snapshot['id']}/finalize",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9532)},
        json={"expected_version": 1},
    )
    assert finalized.status_code == 422
    assert "approved leadership exception" in finalized.json()["detail"]


def test_exception_decision_is_one_time_and_cannot_be_cancelled(client, headers, seeded):
    snapshot = create_negative_snapshot(client, headers, seeded, idn(9540))
    approval = get_exception(seeded, snapshot["id"])

    cancelled = client.post(
        f"/api/v1/team/margin/negative-gm-exceptions/{approval['id']}/decision",
        headers={**headers("admin-a"), "Idempotency-Key": idn(9541)},
        json={"decision": "cancelled", "notes": "Not permitted here."},
    )
    assert cancelled.status_code == 422

    first = client.post(
        f"/api/v1/team/margin/negative-gm-exceptions/{approval['id']}/decision",
        headers={**headers("admin-a"), "Idempotency-Key": idn(9542)},
        json={"decision": "approved", "notes": "Approved once."},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v1/team/margin/negative-gm-exceptions/{approval['id']}/decision",
        headers={**headers("admin-a"), "Idempotency-Key": idn(9543)},
        json={"decision": "rejected", "notes": "Attempted reversal."},
    )
    assert second.status_code == 409


def test_negative_gm_decision_writes_audit_events(client, headers, seeded):
    snapshot = create_negative_snapshot(client, headers, seeded, idn(9550))
    approval = get_exception(seeded, snapshot["id"])

    decision = client.post(
        f"/api/v1/team/margin/negative-gm-exceptions/{approval['id']}/decision",
        headers={**headers("admin-a"), "Idempotency-Key": idn(9551)},
        json={"decision": "approved", "notes": "Audited executive decision."},
    )
    assert decision.status_code == 200

    with seeded.begin() as conn:
        events = conn.execute(select(t.operational_audit).where(
            t.operational_audit.c.tenant_id == idn(1),
            t.operational_audit.c.actor_user_id == idn(13),
            t.operational_audit.c.object_id.in_([approval["id"], snapshot["id"]]),
        )).mappings().all()
    actions = {event["action"] for event in events}
    assert "margin.negative_gm_exception.decided" in actions
    assert "margin.negative_gm_exception.approved" in actions


def test_foreign_tenant_executive_cannot_see_or_decide_exception(client, headers, seeded):
    snapshot = create_negative_snapshot(client, headers, seeded, idn(9560))
    approval = get_exception(seeded, snapshot["id"])

    queue = client.get(
        "/api/v1/team/margin/negative-gm-exceptions",
        headers=headers("admin-foreign"),
    )
    assert queue.status_code == 200
    assert queue.json()["items"] == []

    decision = client.post(
        f"/api/v1/team/margin/negative-gm-exceptions/{approval['id']}/decision",
        headers={**headers("admin-foreign"), "Idempotency-Key": idn(9561)},
        json={"decision": "approved", "notes": "Cross-tenant attempt."},
    )
    assert decision.status_code == 404
