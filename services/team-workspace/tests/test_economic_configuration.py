from datetime import timedelta
from decimal import Decimal

from sqlalchemy import insert, select, update

from margin_engine import GuidelineBands, seed_assumptions
from workspace_api import tables as t
from workspace_api.store import now


def idn(n):
    return f"00000000-0000-0000-0000-{n:012d}"


def assumption_payload(profile="locums_national_1099"):
    assumptions = seed_assumptions(profile).model_copy(
        update={
            "guideline_bands": GuidelineBands(
                recruiter_guideline_min_margin=Decimal("0.20"),
                delivery_manager_discussion_min_margin=Decimal("0.10"),
                legacy_workbook_floor=Decimal("0.10"),
            )
        }
    )
    return assumptions.model_dump(mode="json")


def seed_customer(seeded):
    with seeded.begin() as conn:
        conn.execute(insert(t.customers).values(
            id=idn(400),
            tenant_id=idn(1),
            name="Synthetic MSP Customer",
            status="active",
            metadata={},
            created_at=now(),
            updated_at=now(),
        ))
        conn.execute(update(t.jobs).where(
            t.jobs.c.id == idn(200),
            t.jobs.c.tenant_id == idn(1),
        ).values(customer_id=idn(400), division="Locum Tenens", state="TX"))


def margin_payload():
    return {
        "job_id": idn(200),
        "candidate_id": idn(300),
        "recruiter_user_id": idn(10),
        "worker_classification": "1099",
        "assignment_type": "contract",
        "customer_type": "msp_vms",
        "contract_type": "new_contract",
        "candidate_source": "internal_database",
        "shifts_per_week": 5,
        "contract_weeks": 13,
        "shift_length_hours": 8,
        "client_rate_type": "hourly",
        "client_rate_amount": 250,
        "provider_rate_type": "hourly",
        "provider_rate_amount": 150,
    }


def test_margin_snapshot_fails_closed_without_active_assumptions(client, headers, seeded):
    with seeded.begin() as conn:
        conn.execute(update(t.jobs).where(
            t.jobs.c.id == idn(200),
            t.jobs.c.tenant_id == idn(1),
        ).values(division="Locum Tenens", state="TX"))
    response = client.post(
        "/api/v1/team/margin/locums-pay-package-snapshots",
        headers=headers("recruiter-a"),
        json=margin_payload(),
    )
    assert response.status_code == 422
    assert "No active cost assumption set" in response.json()["detail"]


def test_system_admin_creates_versioned_assumptions(client, headers):
    effective = (now() - timedelta(hours=1)).isoformat()
    response = client.post(
        "/api/v1/team/economic-config/assumptions",
        headers=headers("admin-a"),
        json={
            "profile": "locums_national_1099",
            "version": "approved-2026-10-v1",
            "assumption_payload": {
                **assumption_payload(),
                "version": "approved-2026-10-v1",
            },
            "effective_from": effective,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["profile"] == "locums_national_1099"
    assert body["version"] == "approved-2026-10-v1"

    listed = client.get(
        "/api/v1/team/economic-config/assumptions?profile=locums_national_1099",
        headers=headers("manager-a"),
    )
    assert listed.status_code == 200
    assert listed.json()["items"][0]["version"] == "approved-2026-10-v1"


def test_recruiter_cannot_change_protected_assumptions(client, headers):
    response = client.post(
        "/api/v1/team/economic-config/assumptions",
        headers=headers("recruiter-a"),
        json={
            "profile": "locums_national_1099",
            "version": "bad-recruiter-change",
            "assumption_payload": {
                **assumption_payload(),
                "version": "bad-recruiter-change",
            },
            "effective_from": now().isoformat(),
        },
    )
    assert response.status_code == 403


def test_customer_msp_rule_overrides_profile_default_and_is_snapshotted(client, headers, seeded):
    seed_customer(seeded)
    effective = (now() - timedelta(hours=1)).isoformat()

    assumptions = {
        **assumption_payload(),
        "version": "approved-2026-10-v1",
        "default_msp_fee_rate": "0.06",
    }
    created_assumptions = client.post(
        "/api/v1/team/economic-config/assumptions",
        headers=headers("admin-a"),
        json={
            "profile": "locums_national_1099",
            "version": "approved-2026-10-v1",
            "assumption_payload": assumptions,
            "effective_from": effective,
        },
    )
    assert created_assumptions.status_code == 201

    rule = client.post(
        "/api/v1/team/economic-config/customers",
        headers=headers("admin-a"),
        json={
            "customer_id": idn(400),
            "calculation_profile": "locums_national_1099",
            "version": "msp-8pct-v1",
            "rule_payload": {
                "msp_fee_rate": 0.08,
                "overhead_rate": 0.04,
            },
            "effective_from": effective,
        },
    )
    assert rule.status_code == 201

    snapshot = client.post(
        "/api/v1/team/margin/locums-pay-package-snapshots",
        headers=headers("recruiter-a"),
        json=margin_payload(),
    )
    assert snapshot.status_code == 201
    body = snapshot.json()
    assert body["assumption_version"] == "approved-2026-10-v1"
    assert body["customer_rule_version"] == "msp-8pct-v1"

    detail = client.get(
        f"/api/v1/team/margin/snapshots/{body['id']}",
        headers=headers("recruiter-a"),
    )
    assert detail.status_code == 200
    result = detail.json()["result_payload"]
    assert float(result["effective_msp_fee_rate"]) == 0.08
    assert result["economic_configuration"]["customer_rule_applied"] is True
    assert result["economic_configuration"]["customer_rule_version"] == "msp-8pct-v1"


def test_customer_rule_history_is_effective_dated_not_rewritten(client, headers, seeded):
    seed_customer(seeded)
    old_effective = now() - timedelta(days=2)
    new_effective = now() - timedelta(days=1)

    first = client.post(
        "/api/v1/team/economic-config/customers",
        headers=headers("admin-a"),
        json={
            "customer_id": idn(400),
            "calculation_profile": "locums_national_1099",
            "version": "customer-v1",
            "rule_payload": {"msp_fee_rate": 0.06},
            "effective_from": old_effective.isoformat(),
        },
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/team/economic-config/customers",
        headers=headers("admin-a"),
        json={
            "customer_id": idn(400),
            "calculation_profile": "locums_national_1099",
            "version": "customer-v2",
            "rule_payload": {"msp_fee_rate": 0.08},
            "effective_from": new_effective.isoformat(),
        },
    )
    assert second.status_code == 201

    with seeded.begin() as conn:
        v1 = conn.execute(select(t.customer_economic_rules).where(
            t.customer_economic_rules.c.tenant_id == idn(1),
            t.customer_economic_rules.c.customer_id == idn(400),
            t.customer_economic_rules.c.version == "customer-v1",
        )).mappings().one()
        v2 = conn.execute(select(t.customer_economic_rules).where(
            t.customer_economic_rules.c.tenant_id == idn(1),
            t.customer_economic_rules.c.customer_id == idn(400),
            t.customer_economic_rules.c.version == "customer-v2",
        )).mappings().one()

    assert v1["effective_to"] is not None
    assert v2["effective_to"] is None


def test_recruiter_cannot_manually_override_msp_fee(client, headers, seeded):
    seed_customer(seeded)
    payload = margin_payload()
    payload["msp_fee_rate_override"] = 0.01
    response = client.post(
        "/api/v1/team/margin/locums-pay-package-snapshots",
        headers=headers("recruiter-a"),
        json=payload,
    )
    assert response.status_code == 422
