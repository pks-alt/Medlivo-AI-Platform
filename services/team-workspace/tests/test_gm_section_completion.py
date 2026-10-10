from datetime import timedelta
from decimal import Decimal

from sqlalchemy import insert

from margin_engine import seed_assumptions
from workspace_api import tables as t
from workspace_api.store import now


def idn(n):
    return f"00000000-0000-0000-0000-{n:012d}"


def seed_margin_rows(seeded):
    assumptions = seed_assumptions("locums_national_1099")
    with seeded.begin() as conn:
        conn.execute(insert(t.cost_assumption_sets).values(
            id=idn(1600),
            tenant_id=idn(1),
            profile=assumptions.profile,
            version=assumptions.version,
            assumption_payload=assumptions.model_dump(mode="json"),
            status="active",
            effective_from=now() - timedelta(days=1),
            effective_to=None,
            created_by=idn(13),
            created_at=now() - timedelta(days=1),
        ))
        rows = [
            (1610, 200, 300, 10, 1, "within_guideline", "draft", "0.20"),
            (1611, 200, 300, 10, 2, "within_guideline", "finalized", "0.22"),
            (1612, 201, 301, 11, 1, "discuss_delivery_manager", "draft", "0.12"),
            (1613, 202, 302, 15, 1, "negative_gm", "hard_exception_required", "-0.03"),
        ]
        for sid, job, candidate, recruiter, version, guideline, lifecycle, gm in rows:
            conn.execute(insert(t.margin_snapshots).values(
                id=idn(sid),
                tenant_id=idn(1),
                job_id=idn(job),
                candidate_id=idn(candidate),
                recruiter_user_id=idn(recruiter),
                calculation_profile="locums_national_1099",
                assumption_set_id=idn(1600),
                assumption_version=assumptions.version,
                version=version,
                input_payload={"workflow": "test"},
                result_payload={
                    "gross_margin_percent": gm,
                    "gross_margin_per_week": "500",
                    "gross_margin_assignment": "6500",
                },
                guideline_status=guideline,
                lifecycle_status=lifecycle,
                customer_rule_id=None,
                customer_rule_version=None,
                created_by=idn(recruiter),
                created_at=now() + timedelta(minutes=version),
                finalized_by=idn(recruiter) if lifecycle == "finalized" else None,
                finalized_at=now() if lifecycle == "finalized" else None,
            ))


def test_system_admin_bootstraps_all_approved_profiles_once(client, headers):
    first = client.post(
        "/api/v1/team/economic-config/bootstrap-assumptions",
        headers={**headers("admin-a"), "Idempotency-Key": idn(9700)},
        json={},
    )
    assert first.status_code == 200
    body = first.json()
    assert body["complete"] is True
    assert len(body["created"]) == 6
    assert {x["profile"] for x in body["created"]} == {
        "nursing_allied_ca_w2",
        "nursing_allied_national_w2",
        "rehabilitation_ca_w2",
        "rehabilitation_national_w2",
        "locums_ca_w2",
        "locums_national_1099",
    }

    second = client.post(
        "/api/v1/team/economic-config/bootstrap-assumptions",
        headers={**headers("admin-a"), "Idempotency-Key": idn(9701)},
        json={},
    )
    assert second.status_code == 200
    assert second.json()["created"] == []
    assert len(second.json()["existing"]) == 6


def test_recruiter_cannot_bootstrap_company_assumptions(client, headers):
    response = client.post(
        "/api/v1/team/economic-config/bootstrap-assumptions",
        headers={**headers("recruiter-a"), "Idempotency-Key": idn(9702)},
        json={},
    )
    assert response.status_code == 403


def test_recruiter_margin_history_is_scoped_to_own_packages(client, headers, seeded):
    seed_margin_rows(seeded)
    response = client.get(
        "/api/v1/team/margin/history?limit=100",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert {x["recruiter_user_id"] for x in items} == {idn(10)}
    assert [x["version"] for x in items] == [2, 1]


def test_delivery_manager_margin_history_and_summary_are_team_scoped(client, headers, seeded):
    seed_margin_rows(seeded)
    history = client.get(
        "/api/v1/team/margin/history?limit=100",
        headers=headers("manager-a"),
    )
    assert history.status_code == 200
    recruiter_ids = {x["recruiter_user_id"] for x in history.json()["items"]}
    assert recruiter_ids == {idn(10), idn(11)}
    assert idn(15) not in recruiter_ids

    summary = client.get(
        "/api/v1/team/margin/management-summary",
        headers=headers("manager-a"),
    )
    assert summary.status_code == 200
    totals = summary.json()["totals"]
    assert totals["current_packages"] == 2
    assert totals["finalized"] == 1
    assert totals["discussion_required"] == 1
    assert totals["negative_gm"] == 0
    assert abs(totals["average_gm_percent"] - 0.17) < 0.000001


def test_executive_margin_summary_is_company_wide_and_latest_version_only(client, headers, seeded):
    seed_margin_rows(seeded)
    response = client.get(
        "/api/v1/team/margin/management-summary",
        headers=headers("admin-a"),
    )
    assert response.status_code == 200
    body = response.json()
    totals = body["totals"]
    assert totals["current_packages"] == 3
    assert totals["finalized"] == 1
    assert totals["discussion_required"] == 1
    assert totals["negative_gm"] == 1
    # Job 200 / candidate 300 version 2 replaces version 1 in the current view.
    assert abs(totals["average_gm_percent"] - ((0.22 + 0.12 - 0.03) / 3)) < 0.000001


def test_manager_cannot_see_other_team_negative_margin_in_history(client, headers, seeded):
    seed_margin_rows(seeded)
    response = client.get(
        "/api/v1/team/margin/history?job_id=" + idn(202),
        headers=headers("manager-a"),
    )
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_system_admin_customer_economics_lists_names_and_rules(client, headers, seeded):
    with seeded.begin() as conn:
        conn.execute(insert(t.customers).values(
            id=idn(1700),
            tenant_id=idn(1),
            name="Synthetic Economic Customer",
            status="active",
            metadata={},
            created_at=now(),
            updated_at=now(),
        ))

    customers = client.get(
        "/api/v1/team/economic-config/customers",
        headers=headers("admin-a"),
    )
    assert customers.status_code == 200
    assert any(x["name"] == "Synthetic Economic Customer" for x in customers.json()["items"])

    rule = client.post(
        "/api/v1/team/economic-config/customers",
        headers={**headers("admin-a"), "Idempotency-Key": idn(9703)},
        json={
            "customer_id": idn(1700),
            "calculation_profile": "nursing_allied_national_w2",
            "version": "synthetic-customer-rule-v1",
            "rule_payload": {"msp_fee_rate": 0.07, "overhead_rate": 0.04},
            "effective_from": (now() - timedelta(minutes=1)).isoformat(),
        },
    )
    assert rule.status_code == 201

    rules = client.get(
        "/api/v1/team/economic-config/customer-rules",
        headers=headers("admin-a"),
    )
    assert rules.status_code == 200
    item = next(x for x in rules.json()["items"] if x["version"] == "synthetic-customer-rule-v1")
    assert item["customer_name"] == "Synthetic Economic Customer"
    assert float(item["rule_payload"]["msp_fee_rate"]) == 0.07


def test_recruiter_cannot_view_company_customer_economic_rules(client, headers):
    customers = client.get(
        "/api/v1/team/economic-config/customers",
        headers=headers("recruiter-a"),
    )
    assert customers.status_code == 403
    rules = client.get(
        "/api/v1/team/economic-config/customer-rules",
        headers=headers("recruiter-a"),
    )
    assert rules.status_code == 403
