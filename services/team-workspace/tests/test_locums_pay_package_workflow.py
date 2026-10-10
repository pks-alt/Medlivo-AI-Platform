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


def set_job(seeded, division, state):
    with seeded.begin() as conn:
        conn.execute(update(t.jobs).where(
            t.jobs.c.id == idn(200),
            t.jobs.c.tenant_id == idn(1),
        ).values(division=division, state=state))


def payload(worker_classification):
    is_1099 = worker_classification == "1099"
    return {
        "job_id": idn(200),
        "candidate_id": idn(300),
        "recruiter_user_id": idn(10),
        "worker_classification": worker_classification,
        "assignment_type": "contract",
        "customer_type": "msp_vms",
        "contract_type": "new_contract",
        "candidate_source": "internal_database",
        "shifts_per_week": 2 if is_1099 else 5,
        "contract_weeks": 13,
        "shift_length_hours": 10 if is_1099 else 8,
        "client_rate_type": "hourly",
        "client_rate_amount": 410 if is_1099 else 220,
        "provider_rate_type": "hourly",
        "provider_rate_amount": 280 if is_1099 else 130,
    }


def test_ca_w2_locums_auto_selects_ca_w2_calculator(client, headers, seeded):
    seed_assumption(seeded, "locums_ca_w2", 1400)
    set_job(seeded, "Locum Tenens", "CA")

    response = client.post(
        "/api/v1/team/margin/locums-pay-package-snapshots",
        headers=headers("recruiter-a"),
        json=payload("w2"),
    )
    assert response.status_code == 201
    snapshot = response.json()
    assert snapshot["calculation_profile"] == "locums_ca_w2"

    detail = client.get(
        f"/api/v1/team/margin/snapshots/{snapshot['id']}",
        headers=headers("recruiter-a"),
    ).json()
    assert detail["result_payload"]["calculator_source"] == "Medlivo CA Locums W-2 GM Calculator"
    assert detail["result_payload"]["pay_package"]["gross_client_billing_per_week"] == "8800.000000"
    assert detail["result_payload"]["pay_package"]["provider_compensation_per_week"] == "5200.000000"


def test_1099_locums_auto_selects_national_1099_calculator(client, headers, seeded):
    seed_assumption(seeded, "locums_national_1099", 1401)
    set_job(seeded, "Locum Tenens", "TX")

    response = client.post(
        "/api/v1/team/margin/locums-pay-package-snapshots",
        headers=headers("recruiter-a"),
        json=payload("1099"),
    )
    assert response.status_code == 201
    snapshot = response.json()
    assert snapshot["calculation_profile"] == "locums_national_1099"

    detail = client.get(
        f"/api/v1/team/margin/snapshots/{snapshot['id']}",
        headers=headers("recruiter-a"),
    ).json()
    assert detail["result_payload"]["calculator_source"] == "Medlivo Locums 1099 GM Calculator"
    assert detail["result_payload"]["pay_package"]["gross_client_billing_per_week"] == "8200.000000"
    assert detail["result_payload"]["pay_package"]["provider_compensation_per_week"] == "5600.000000"


def test_1099_locums_remains_1099_even_for_california_job(client, headers, seeded):
    seed_assumption(seeded, "locums_national_1099", 1402)
    set_job(seeded, "Locum Tenens", "California")

    response = client.post(
        "/api/v1/team/margin/locums-pay-package-snapshots",
        headers=headers("recruiter-a"),
        json=payload("1099"),
    )
    assert response.status_code == 201
    assert response.json()["calculation_profile"] == "locums_national_1099"


def test_non_california_w2_locums_fails_closed(client, headers, seeded):
    set_job(seeded, "Locum Tenens", "Texas")
    response = client.post(
        "/api/v1/team/margin/locums-pay-package-snapshots",
        headers=headers("recruiter-a"),
        json=payload("w2"),
    )
    assert response.status_code == 422
    assert "California only" in response.json()["detail"]


def test_non_locums_job_cannot_use_locums_workflow(client, headers, seeded):
    set_job(seeded, "Rehabilitation", "CA")
    response = client.post(
        "/api/v1/team/margin/locums-pay-package-snapshots",
        headers=headers("recruiter-a"),
        json=payload("1099"),
    )
    assert response.status_code == 422
    assert "Locum Tenens job" in response.json()["detail"]


def test_recruiter_cannot_choose_locums_profile_directly(client, headers, seeded):
    seed_assumption(seeded, "locums_national_1099", 1403)
    response = client.post(
        "/api/v1/team/margin/snapshots",
        headers=headers("recruiter-a"),
        json={
            "job_id": idn(200),
            "candidate_id": idn(300),
            "recruiter_user_id": idn(10),
            "profile": "locums_national_1099",
            "division": "locum_tenens",
            "customer_type": "direct",
            "assignment_weeks_equivalent": 13,
            "gross_client_billing_per_week": 8200,
            "contractor_compensation_per_week": 5600,
        },
    )
    assert response.status_code == 422
    assert "structured pay package workflow" in response.json()["detail"]


def test_locums_worker_classification_is_not_a_profile_field(client, headers, seeded):
    seed_assumption(seeded, "locums_national_1099", 1404)
    set_job(seeded, "Locum Tenens", "TX")
    body = payload("1099")
    body["profile"] = "locums_ca_w2"
    response = client.post(
        "/api/v1/team/margin/locums-pay-package-snapshots",
        headers=headers("recruiter-a"),
        json=body,
    )
    assert response.status_code == 422
