from datetime import date
from uuid import uuid4

from workspace_api import tables as t
from sqlalchemy import insert
from workspace_api.store import now
from .conftest import idn


def test_manager_can_create_rehab_job_intake_batch(client, headers):
    response = client.post(
        "/api/v1/team/job-intake/batches",
        headers=headers("manager-a"),
        json={
            "customer_name": "Synthetic Rehab Customer",
            "division": "Rehabilitation",
            "source_filename": "rehab-jobs.xlsx",
            "mapping": {
                "Posting Title": "title",
                "Facility Location : City": "city",
                "Facility Location : State/Province": "state",
            },
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["team_id"] == idn(30)
    assert body["status"] == "draft"
    assert body["row_count"] == 0


def test_recruiter_cannot_create_job_intake_batch(client, headers):
    response = client.post(
        "/api/v1/team/job-intake/batches",
        headers=headers("recruiter-a"),
        json={
            "customer_name": "Synthetic Customer",
            "division": "Rehabilitation",
            "source_filename": "jobs.xlsx",
            "mapping": {},
        },
    )
    assert response.status_code == 403


def test_manager_can_save_customer_mapping(client, headers):
    response = client.put(
        "/api/v1/team/job-intake/mappings",
        headers=headers("manager-a"),
        json={
            "customer_name": "Synthetic Rehab Customer",
            "division": "Rehabilitation",
            "mapping": {
                "Posting Title": "title",
                "Bill Rate": "bill_rate",
                "Hours Per Week": "hours_per_week",
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["mapping"]["Bill Rate"] == "bill_rate"

    listed = client.get(
        "/api/v1/team/job-intake/mappings?division=Rehabilitation",
        headers=headers("manager-a"),
    )
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1


def test_recruiter_sets_own_weekly_goal(client, headers):
    response = client.put(
        f"/api/v1/team/recruiters/{idn(10)}/weekly-goals",
        headers=headers("recruiter-a"),
        json={
            "week_start": "2026-10-05",
            "submissions_target": 12,
            "interviews_target": 5,
            "closures_target": 2,
            "priority_jobs_target": 8,
            "notes": "Focus on priority PT and OT jobs",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["submissions_target"] == 12
    assert body["interviews_target"] == 5
    assert body["closures_target"] == 2


def test_recruiter_cannot_set_another_recruiters_goal(client, headers):
    response = client.put(
        f"/api/v1/team/recruiters/{idn(11)}/weekly-goals",
        headers=headers("recruiter-a"),
        json={
            "week_start": "2026-10-05",
            "submissions_target": 10,
            "interviews_target": 4,
            "closures_target": 1,
            "priority_jobs_target": 5,
        },
    )
    assert response.status_code == 403


def test_weekly_goal_requires_monday(client, headers):
    response = client.put(
        f"/api/v1/team/recruiters/{idn(10)}/weekly-goals",
        headers=headers("recruiter-a"),
        json={
            "week_start": "2026-10-06",
            "submissions_target": 10,
            "interviews_target": 4,
            "closures_target": 1,
            "priority_jobs_target": 5,
        },
    )
    assert response.status_code == 422


def test_manager_weekly_review_combines_goals_and_automatic_snapshot(client, headers, seeded):
    goal = client.put(
        f"/api/v1/team/recruiters/{idn(10)}/weekly-goals",
        headers=headers("recruiter-a"),
        json={
            "week_start": "2026-10-05",
            "submissions_target": 12,
            "interviews_target": 5,
            "closures_target": 2,
            "priority_jobs_target": 8,
        },
    )
    assert goal.status_code == 200

    with seeded.begin() as conn:
        conn.execute(insert(t.weekly_snapshots).values(
            id=str(uuid4()), tenant_id=idn(1), team_id=idn(30), recruiter_user_id=idn(10),
            week_start=date(2026, 10, 5), submissions_actual=10, interviews_actual=4,
            closures_actual=2, offers_actual=3, starts_actual=1, qualified_actual=18,
            responses_actual=31, source_breakdown={"jobdiva": True, "platform": True},
            generated_at=now(),
        ))

    response = client.get(
        "/api/v1/team/manager/weekly-review?week_start=2026-10-05",
        headers=headers("manager-a"),
    )
    assert response.status_code == 200
    item = next(x for x in response.json()["recruiters"] if x["id"] == idn(10))
    assert item["targets"]["submissions"] == 12
    assert item["actuals"]["submissions"] == 10
    assert item["actuals"]["interviews"] == 4
    assert item["actuals"]["closures"] == 2


def test_manager_cannot_review_other_team(client, headers):
    response = client.get(
        f"/api/v1/team/manager/weekly-review?week_start=2026-10-05&team_id={idn(31)}",
        headers=headers("manager-a"),
    )
    assert response.status_code == 403
