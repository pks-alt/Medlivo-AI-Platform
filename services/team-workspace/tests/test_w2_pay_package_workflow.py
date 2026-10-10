from datetime import timedelta

from sqlalchemy import insert, update

from margin_engine import seed_assumptions
from workspace_api import tables as t
from workspace_api.store import now


def idn(n):
    return f"00000000-0000-0000-0000-{n:012d}"


def seed_assumption(seeded, profile, row_id):
    assumptions = seed_assumptions(profile)
    with seeded.begin() as conn:
        conn.execute(insert(t.cost_assumption_sets).values(
            id=idn(row_id),
            tenant_id=idn(1),
            profile=profile,
            version=assumptions.version,
            assumption_payload=assumptions.model_dump(mode="json"),
            status="active",
            effective_from=now() - timedelta(hours=1),
            effective_to=None,
            created_by=idn(13),
            created_at=now(),
        ))


def nursing_payload():
    return {
        "job_id": idn(200),
        "candidate_id": idn(300),
        "recruiter_user_id": idn(10),
        "customer_type": "msp_vms",
        "contract_type": "new_contract",
        "candidate_source": "vivian",
        "contract_weeks": 13,
        "shift_length_hours": 8,
        "shifts_per_week": 5,
        "regular_client_bill_rate": 139,
        "ot_client_bill_rate": 139,
        "double_time_client_bill_rate": 139,
        "taxable_base_hourly_pay": 33,
        "housing_stipend_per_hour": 38,
        "meals_incidentals_stipend_per_hour": 28,
        "callback_pay_rate": 33,
        "orientation_hours": 12,
    }


def rehab_payload():
    return {
        "job_id": idn(200),
        "candidate_id": idn(300),
        "recruiter_user_id": idn(10),
        "customer_type": "msp_vms",
        "contract_type": "new_contract",
        "candidate_source": "other",
        "contract_weeks": 13,
        "shift_length_hours": 12,
        "shifts_per_week": 3,
        "regular_client_bill_rate": 90,
        "taxable_base_hourly_pay": 18,
        "housing_stipend_per_hour": 28,
        "meals_incidentals_stipend_per_hour": 11.6,
        "on_call_client_bill_rate": 7,
        "clinician_on_call_pay_rate": 0,
        "callback_pay_rate": 18,
        "orientation_hours": 16,
    }


def test_nursing_california_job_automatically_uses_anand_ca_profile(client, headers, seeded):
    seed_assumption(seeded, "nursing_allied_ca_w2", 1300)
    with seeded.begin() as conn:
        conn.execute(update(t.jobs).where(
            t.jobs.c.id == idn(200),
            t.jobs.c.tenant_id == idn(1),
        ).values(division="Nursing & Allied", state="CA"))

    response = client.post(
        "/api/v1/team/margin/w2-pay-package-snapshots",
        headers=headers("recruiter-a"),
        json=nursing_payload(),
    )
    assert response.status_code == 201
    snapshot = response.json()
    assert snapshot["calculation_profile"] == "nursing_allied_ca_w2"
    assert snapshot["assumption_version"] == "anand-2026-10-nursing-ca-v1"

    detail = client.get(
        f"/api/v1/team/margin/snapshots/{snapshot['id']}",
        headers=headers("recruiter-a"),
    )
    assert detail.status_code == 200
    result = detail.json()["result_payload"]
    assert result["calculator_source"] == "Anand - Medlivo Recruiter GM Calculator"
    assert result["pay_package"]["gross_client_billing_per_week"] == "5560.000000"
    assert result["pay_package"]["taxable_wages_per_week"] == "1320.000000"
    assert result["pay_package"]["recurring_non_taxable_cost_per_week"] == "2640.000000"


def test_rehab_national_job_automatically_uses_prachi_national_profile(client, headers, seeded):
    seed_assumption(seeded, "rehabilitation_national_w2", 1301)
    with seeded.begin() as conn:
        conn.execute(update(t.jobs).where(
            t.jobs.c.id == idn(200),
            t.jobs.c.tenant_id == idn(1),
        ).values(division="Rehabilitation", state="Ohio"))

    response = client.post(
        "/api/v1/team/margin/w2-pay-package-snapshots",
        headers=headers("recruiter-a"),
        json=rehab_payload(),
    )
    assert response.status_code == 201
    snapshot = response.json()
    assert snapshot["calculation_profile"] == "rehabilitation_national_w2"
    assert snapshot["assumption_version"] == "prachi-2026-10-rehab-national-v1"

    detail = client.get(
        f"/api/v1/team/margin/snapshots/{snapshot['id']}",
        headers=headers("recruiter-a"),
    )
    result = detail.json()["result_payload"]
    assert result["calculator_source"] == "Prachi Medlivo Recruiter GM Calculator"
    assert result["pay_package"]["gross_client_billing_per_week"] == "3240.000000"
    assert result["pay_package"]["taxable_wages_per_week"] == "648.000000"
    assert result["pay_package"]["recurring_non_taxable_cost_per_week"] == "1425.600000"


def test_rehab_california_automatically_selects_prachi_ca_not_anand(client, headers, seeded):
    seed_assumption(seeded, "rehabilitation_ca_w2", 1302)
    with seeded.begin() as conn:
        conn.execute(update(t.jobs).where(
            t.jobs.c.id == idn(200),
            t.jobs.c.tenant_id == idn(1),
        ).values(division="Rehabilitation", state="California"))

    payload = rehab_payload()
    payload.update({
        "shift_length_hours": 8,
        "shifts_per_week": 5,
        "regular_client_bill_rate": 90,
        "taxable_base_hourly_pay": 24,
        "housing_stipend_per_hour": 27,
        "meals_incidentals_stipend_per_hour": 20,
        "orientation_hours": 0,
        "completion_bonus": 350,
        "contract_type": "extension",
    })
    response = client.post(
        "/api/v1/team/margin/w2-pay-package-snapshots",
        headers=headers("recruiter-a"),
        json=payload,
    )
    assert response.status_code == 201
    assert response.json()["calculation_profile"] == "rehabilitation_ca_w2"

    detail = client.get(
        f"/api/v1/team/margin/snapshots/{response.json()['id']}",
        headers=headers("recruiter-a"),
    ).json()
    assert detail["result_payload"]["calculator_source"] == "Prachi Medlivo Recruiter GM Calculator"


def test_w2_profile_is_not_selected_by_recruiter(client, headers, seeded):
    seed_assumption(seeded, "nursing_allied_ca_w2", 1303)
    with seeded.begin() as conn:
        conn.execute(update(t.jobs).where(
            t.jobs.c.id == idn(200),
            t.jobs.c.tenant_id == idn(1),
        ).values(division="Nursing & Allied", state="CA"))

    payload = nursing_payload()
    payload["profile"] = "rehabilitation_ca_w2"
    response = client.post(
        "/api/v1/team/margin/w2-pay-package-snapshots",
        headers=headers("recruiter-a"),
        json=payload,
    )
    assert response.status_code == 422


def test_raw_margin_endpoint_cannot_bypass_nursing_rehab_package_rules(client, headers, seeded):
    seed_assumption(seeded, "nursing_allied_ca_w2", 1304)
    response = client.post(
        "/api/v1/team/margin/snapshots",
        headers=headers("recruiter-a"),
        json={
            "job_id": idn(200),
            "candidate_id": idn(300),
            "recruiter_user_id": idn(10),
            "profile": "nursing_allied_ca_w2",
            "division": "nursing_allied",
            "customer_type": "direct",
            "assignment_weeks_equivalent": 13,
            "gross_client_billing_per_week": 5000,
            "taxable_wages_per_week": 1000,
        },
    )
    assert response.status_code == 422
    assert "structured W-2 pay package workflow" in response.json()["detail"]


def test_missing_job_division_or_state_fails_closed(client, headers, seeded):
    seed_assumption(seeded, "nursing_allied_ca_w2", 1305)

    missing_division = client.post(
        "/api/v1/team/margin/w2-pay-package-snapshots",
        headers=headers("recruiter-a"),
        json=nursing_payload(),
    )
    assert missing_division.status_code == 422
    assert "Job division is required" in missing_division.json()["detail"]

    with seeded.begin() as conn:
        conn.execute(update(t.jobs).where(
            t.jobs.c.id == idn(200),
            t.jobs.c.tenant_id == idn(1),
        ).values(division="Nursing & Allied", state=None))

    missing_state = client.post(
        "/api/v1/team/margin/w2-pay-package-snapshots",
        headers=headers("recruiter-a"),
        json=nursing_payload(),
    )
    assert missing_state.status_code == 422
    assert "Job state is required" in missing_state.json()["detail"]


def test_locums_job_cannot_enter_nursing_rehab_w2_workflow(client, headers, seeded):
    with seeded.begin() as conn:
        conn.execute(update(t.jobs).where(
            t.jobs.c.id == idn(200),
            t.jobs.c.tenant_id == idn(1),
        ).values(division="Locum Tenens", state="CA"))

    response = client.post(
        "/api/v1/team/margin/w2-pay-package-snapshots",
        headers=headers("recruiter-a"),
        json=nursing_payload(),
    )
    assert response.status_code == 422
    assert "only for Nursing & Allied or Rehabilitation" in response.json()["detail"]
