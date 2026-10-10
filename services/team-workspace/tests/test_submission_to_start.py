from datetime import timedelta, date

from sqlalchemy import insert

from workspace_api import tables as t
from workspace_api.store import now


def idn(n):
    return f"00000000-0000-0000-0000-{n:012d}"


def seed_funnel(seeded):
    ts = now()
    with seeded.begin() as conn:
        conn.execute(insert(t.submission_projections), [
            {
                "id": idn(1800), "tenant_id": idn(1), "job_id": idn(200),
                "candidate_id": idn(300), "recruiter_user_id": idn(10),
                "source_system": "jobdiva", "source_submission_id": "SUB-200-300",
                "source_status": "submitted", "submitted_at": ts - timedelta(days=3),
                "client_response_at": None, "source_updated_at": ts,
                "raw_payload": {"source": "synthetic"}, "synced_at": ts,
            },
            {
                "id": idn(1801), "tenant_id": idn(1), "job_id": idn(201),
                "candidate_id": idn(301), "recruiter_user_id": idn(11),
                "source_system": "jobdiva", "source_submission_id": "SUB-201-301",
                "source_status": "submitted", "submitted_at": ts - timedelta(days=2),
                "client_response_at": None, "source_updated_at": ts,
                "raw_payload": {}, "synced_at": ts,
            },
            {
                "id": idn(1802), "tenant_id": idn(1), "job_id": idn(202),
                "candidate_id": idn(302), "recruiter_user_id": idn(15),
                "source_system": "jobdiva", "source_submission_id": "SUB-202-302",
                "source_status": "submitted", "submitted_at": ts - timedelta(days=1),
                "client_response_at": None, "source_updated_at": ts,
                "raw_payload": {}, "synced_at": ts,
            },
        ])
        conn.execute(insert(t.interview_projections).values(
            id=idn(1810), tenant_id=idn(1), job_id=idn(200),
            candidate_id=idn(300), submission_projection_id=idn(1800),
            source_system="jobdiva", source_interview_id="INT-200-300",
            source_status="scheduled", interview_type="client_video",
            scheduled_at=ts + timedelta(days=1), completed_at=None,
            outcome=None, outcome_at=None, source_updated_at=ts,
            raw_payload={}, synced_at=ts,
        ))
        conn.execute(insert(t.offer_projections).values(
            id=idn(1820), tenant_id=idn(1), job_id=idn(200),
            candidate_id=idn(300), submission_projection_id=idn(1800),
            source_system="jobdiva", source_offer_id="OFF-200-300",
            source_status="accepted", offered_at=ts - timedelta(hours=10),
            accepted_at=ts - timedelta(hours=2), declined_at=None,
            decline_reason=None, source_updated_at=ts,
            raw_payload={}, synced_at=ts,
        ))
        conn.execute(insert(t.placement_projections).values(
            id=idn(1830), tenant_id=idn(1), job_id=idn(200),
            candidate_id=idn(300), source_system="jobdiva",
            source_placement_id="PLC-200-300", source_status="active",
            placement_status="pre_start", planned_start_date=date(2026, 10, 20),
            actual_start_date=None, planned_end_date=date(2027, 1, 18),
            actual_end_date=None, source_updated_at=ts,
            raw_payload={}, synced_at=ts,
        ))


def test_recruiter_funnel_is_scoped_to_own_submissions(client, headers, seeded):
    seed_funnel(seeded)
    response = client.get("/api/v1/team/funnel", headers=headers("recruiter-a"))
    assert response.status_code == 200
    body = response.json()
    assert body["totals"]["submissions"] == 1
    assert body["totals"]["interviews"] == 1
    assert body["totals"]["offers"] == 1
    assert body["totals"]["placements"] == 1
    assert body["items"][0]["job_id"] == idn(200)
    assert body["items"][0]["candidate_id"] == idn(300)


def test_delivery_manager_funnel_is_team_scoped(client, headers, seeded):
    seed_funnel(seeded)
    response = client.get("/api/v1/team/funnel", headers=headers("manager-a"))
    assert response.status_code == 200
    ids = {(x["job_id"], x["candidate_id"]) for x in response.json()["items"]}
    assert ids == {(idn(200), idn(300)), (idn(201), idn(301))}
    assert (idn(202), idn(302)) not in ids


def test_executive_funnel_is_company_wide(client, headers, seeded):
    seed_funnel(seeded)
    response = client.get("/api/v1/team/funnel", headers=headers("admin-a"))
    assert response.status_code == 200
    assert response.json()["totals"]["submissions"] == 3


def test_funnel_detail_combines_jobdiva_projections(client, headers, seeded):
    seed_funnel(seeded)
    response = client.get(
        f"/api/v1/team/funnel/{idn(200)}/{idn(300)}",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["submissions"][0]["source_submission_id"] == "SUB-200-300"
    assert body["interviews"][0]["source_interview_id"] == "INT-200-300"
    assert body["offers"][0]["source_offer_id"] == "OFF-200-300"
    assert body["placements"][0]["source_placement_id"] == "PLC-200-300"
    assert body["start_readiness"] is None


def test_recruiter_cannot_view_other_recruiter_funnel_detail(client, headers, seeded):
    seed_funnel(seeded)
    response = client.get(
        f"/api/v1/team/funnel/{idn(201)}/{idn(301)}",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 404


def test_high_start_risk_requires_reason_and_next_action(client, headers, seeded):
    seed_funnel(seeded)
    missing_reason = client.put(
        f"/api/v1/team/funnel/{idn(200)}/{idn(300)}/start-readiness",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9800)},
        json={
            "status": "in_progress",
            "risk_level": "high",
            "risk_reason": None,
            "next_action": "Collect credential",
            "owner_user_id": idn(10),
            "due_at": (now() + timedelta(days=1)).isoformat(),
            "expected_version": 0,
        },
    )
    assert missing_reason.status_code == 422

    missing_action = client.put(
        f"/api/v1/team/funnel/{idn(200)}/{idn(300)}/start-readiness",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9801)},
        json={
            "status": "in_progress",
            "risk_level": "critical",
            "risk_reason": "License verification pending",
            "next_action": None,
            "owner_user_id": idn(10),
            "due_at": (now() + timedelta(days=1)).isoformat(),
            "expected_version": 0,
        },
    )
    assert missing_action.status_code == 422


def test_start_readiness_required_items_gate_ready_status(client, headers, seeded):
    seed_funnel(seeded)
    created = client.put(
        f"/api/v1/team/funnel/{idn(200)}/{idn(300)}/start-readiness",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9810)},
        json={
            "status": "in_progress",
            "risk_level": "high",
            "risk_reason": "Background check pending",
            "next_action": "Receive final background result",
            "owner_user_id": idn(10),
            "due_at": (now() + timedelta(days=1)).isoformat(),
            "expected_version": 0,
        },
    )
    assert created.status_code == 200
    assert created.json()["version"] == 1

    item = client.put(
        f"/api/v1/team/funnel/{idn(200)}/{idn(300)}/start-readiness/items",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9811)},
        json={
            "item_key": "background_check",
            "label": "Background Check",
            "category": "compliance",
            "status": "pending",
            "required": True,
            "due_at": (now() + timedelta(days=1)).isoformat(),
            "notes": "Vendor result pending",
        },
    )
    assert item.status_code == 200

    blocked = client.put(
        f"/api/v1/team/funnel/{idn(200)}/{idn(300)}/start-readiness",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9812)},
        json={
            "status": "ready",
            "risk_level": "low",
            "risk_reason": None,
            "next_action": None,
            "owner_user_id": idn(10),
            "due_at": None,
            "expected_version": 1,
        },
    )
    assert blocked.status_code == 422
    assert "Required start-readiness items" in blocked.json()["detail"]

    complete = client.put(
        f"/api/v1/team/funnel/{idn(200)}/{idn(300)}/start-readiness/items",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9813)},
        json={
            "item_key": "background_check",
            "label": "Background Check",
            "category": "compliance",
            "status": "complete",
            "required": True,
            "due_at": None,
            "notes": "Cleared",
        },
    )
    assert complete.status_code == 200

    ready = client.put(
        f"/api/v1/team/funnel/{idn(200)}/{idn(300)}/start-readiness",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9814)},
        json={
            "status": "ready",
            "risk_level": "low",
            "risk_reason": None,
            "next_action": "Confirm first-day instructions",
            "owner_user_id": idn(10),
            "due_at": None,
            "expected_version": 1,
        },
    )
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert ready.json()["version"] == 2


def test_start_readiness_is_version_checked(client, headers, seeded):
    seed_funnel(seeded)
    first = client.put(
        f"/api/v1/team/funnel/{idn(200)}/{idn(300)}/start-readiness",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9820)},
        json={
            "status": "in_progress",
            "risk_level": "medium",
            "risk_reason": "Credential packet incomplete",
            "next_action": "Collect missing document",
            "owner_user_id": idn(10),
            "due_at": (now() + timedelta(days=2)).isoformat(),
            "expected_version": 0,
        },
    )
    assert first.status_code == 200

    stale = client.put(
        f"/api/v1/team/funnel/{idn(200)}/{idn(300)}/start-readiness",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9821)},
        json={
            "status": "blocked",
            "risk_level": "high",
            "risk_reason": "Missing document",
            "next_action": "Escalate to candidate",
            "owner_user_id": idn(10),
            "due_at": (now() + timedelta(days=1)).isoformat(),
            "expected_version": 0,
        },
    )
    assert stale.status_code == 409


def test_funnel_projection_fields_are_not_exposed_as_manual_mutations(client, headers, seeded):
    seed_funnel(seeded)
    response = client.put(
        f"/api/v1/team/funnel/{idn(200)}/{idn(300)}/submission",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9830)},
        json={"source_status": "placed"},
    )
    assert response.status_code == 404
