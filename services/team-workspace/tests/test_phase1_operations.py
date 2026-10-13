from datetime import date, timedelta
from uuid import uuid4
from io import BytesIO
from openpyxl import Workbook
from fastapi.testclient import TestClient

from workspace_api import tables as t
from sqlalchemy import insert, update, select
from workspace_api.store import now, WorkspaceStore
from workspace_api.app import build_app
from workspace_api.job_intake_ai import JobIntakeAIResult


def idn(n):
    return f"00000000-0000-0000-0000-{n:012d}"


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

def test_recruiter_monday_goal_locks_after_first_commit(client, headers):
    payload = {
        "week_start": "2026-10-05",
        "submissions_target": 12,
        "interviews_target": 5,
        "closures_target": 2,
        "priority_jobs_target": 8,
        "notes": "Monday commitment",
    }
    first = client.put(
        f"/api/v1/team/recruiters/{idn(10)}/weekly-goals",
        headers=headers("recruiter-a"),
        json=payload,
    )
    assert first.status_code == 200

    changed = dict(payload, submissions_target=20)
    second = client.put(
        f"/api/v1/team/recruiters/{idn(10)}/weekly-goals",
        headers=headers("recruiter-a"),
        json=changed,
    )
    assert second.status_code == 409
    assert "locked" in second.json()["detail"].lower()

    progress = client.get(
        f"/api/v1/team/recruiters/{idn(10)}/weekly-goals?week_start=2026-10-05",
        headers=headers("recruiter-a"),
    )
    assert progress.status_code == 200
    assert progress.json()["goal_set"] is True
    assert progress.json()["goal_locked"] is True
    assert progress.json()["targets"]["submissions"] == 12


def test_manager_can_adjust_locked_monday_commitment(client, headers):
    initial = client.put(
        f"/api/v1/team/recruiters/{idn(10)}/weekly-goals",
        headers=headers("recruiter-a"),
        json={
            "week_start": "2026-10-05",
            "submissions_target": 12,
            "interviews_target": 5,
            "closures_target": 2,
            "priority_jobs_target": 8,
            "notes": "Monday commitment",
        },
    )
    assert initial.status_code == 200

    adjusted = client.put(
        f"/api/v1/team/recruiters/{idn(10)}/weekly-goals",
        headers=headers("manager-a"),
        json={
            "week_start": "2026-10-05",
            "submissions_target": 14,
            "interviews_target": 6,
            "closures_target": 2,
            "priority_jobs_target": 9,
            "notes": "Manager adjustment after Monday review",
        },
    )
    assert adjusted.status_code == 200
    assert adjusted.json()["submissions_target"] == 14
    assert adjusted.json()["notes"] == "Manager adjustment after Monday review"



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
    assert item["goal_set"] is True
    assert item["goal_locked"] is True
    assert item["delivery_status"] == "on_track"
    assert item["attainment"] > 80
    totals = response.json()["totals"]
    assert totals["goals_set"] == 1
    assert totals["submissions_target"] == 12
    assert totals["submissions_actual"] == 10
    assert totals["starts_actual"] == 1


def test_manager_cannot_review_other_team(client, headers):
    response = client.get(
        f"/api/v1/team/manager/weekly-review?week_start=2026-10-05&team_id={idn(31)}",
        headers=headers("manager-a"),
    )
    assert response.status_code == 403


def test_rehab_rows_are_normalized_and_classified(client, headers):
    created = client.post(
        "/api/v1/team/job-intake/batches",
        headers=headers("manager-a"),
        json={
            "customer_name": "Synthetic Rehab Customer",
            "division": "Rehabilitation",
            "source_filename": "rehab-jobs.xlsx",
            "mapping": {
                "Requisition ID": "requisition_id",
                "Posting Title": "title",
                "Location : Name Linked": "facility",
                "Facility Location : City": "city",
                "Facility Location : State/Province": "state",
                "Bill Rate": "bill_rate",
                "Start Date": "start_date",
                "End Date": "end_date",
                "Location : Location Setting": "setting",
                "Hours Per Week": "hours_per_week",
            },
        },
    )
    assert created.status_code == 201
    batch_id = created.json()["id"]

    rows = [
        {
            "Requisition ID": "2026-135775",
            "Posting Title": "Contract PT - Maternity Leave Coverage",
            "Location : Name Linked": "The Terraces at San Joaquin Gardens",
            "Facility Location : City": "Fresno",
            "Facility Location : State/Province": "CA",
            "Bill Rate": 85,
            "Start Date": "2026-11-29",
            "End Date": "2027-02-28",
            "Location : Location Setting": "SNF",
            "Hours Per Week": 32,
        },
        {
            "Requisition ID": "2026-136203",
            "Posting Title": "Contract PT",
            "Location : Name Linked": "St John's United",
            "Facility Location : City": "Billings",
            "Facility Location : State/Province": "MT",
            "Bill Rate": 85,
            "Start Date": "2026-11-01",
            "End Date": "2027-01-31",
            "Location : Location Setting": "IL / AL",
            "Hours Per Week": 32,
        },
        {
            "Requisition ID": "2026-136203",
            "Posting Title": "Contract PT",
            "Location : Name Linked": "St John's United",
            "Facility Location : City": "Billings",
            "Facility Location : State/Province": "MT",
            "Bill Rate": 85,
            "Start Date": "2026-11-01",
            "End Date": "2027-01-31",
            "Location : Location Setting": "IL / AL",
            "Hours Per Week": 32,
        },
        {
            "Requisition ID": "2026-missing-title",
            "Posting Title": "",
            "Location : Name Linked": "Synthetic Facility",
            "Facility Location : City": "Seattle",
            "Facility Location : State/Province": "WA",
            "Start Date": "2026-11-01",
            "Hours Per Week": 40,
        },
    ]
    processed = client.post(
        f"/api/v1/team/job-intake/batches/{batch_id}/rows",
        headers=headers("manager-a"),
        json={"rows": rows},
    )
    assert processed.status_code == 200
    summary = processed.json()
    assert summary["row_count"] == 4
    assert summary["ready_count"] == 0
    assert summary["duplicate_count"] == 1
    assert summary["review_count"] == 3

    reviewed = client.get(
        f"/api/v1/team/job-intake/batches/{batch_id}/items",
        headers=headers("manager-a"),
    )
    assert reviewed.status_code == 200
    items = reviewed.json()["items"]
    assert items[0]["normalized_job"]["facility"] == "The Terraces at San Joaquin Gardens"
    assert items[0]["normalized_job"]["hours_per_week"] == 32
    assert items[2]["status"] == "duplicate"
    assert items[3]["status"] == "review"


def test_manager_can_upload_real_rehab_xlsx(client, headers):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append([
        "Requisition ID", "Posting Title", "Location : Name Linked",
        "Facility Location : City", "Facility Location : State/Province",
        "Bill Rate", "Start Date", "End Date", "Location : Location Setting",
        "Hours Per Week",
    ])
    sheet.append([
        "2026-135775", "Contract PT - Maternity Leave Coverage",
        "The Terraces at San Joaquin Gardens", "Fresno", "CA", 85,
        "11/29/2026", "2/28/2027", "SNF", 32,
    ])
    sheet.append([
        "2026-136203", "Contract PT", "St John's United", "Billings", "MT", 85,
        "11/1/2026", "1/31/2027", "IL / AL", 32,
    ])
    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()

    request_headers = headers("manager-a")
    response = client.post(
        "/api/v1/team/job-intake/upload",
        headers=request_headers,
        data={"customer_name": "Synthetic Rehab Customer", "division": "Rehabilitation"},
        files={"source_file": (
            "rehab-jobs.xlsx", buffer.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["row_count"] == 2
    assert body["ready_count"] == 0
    assert body["review_count"] == 2
    assert body["duplicate_count"] == 0
    assert body["mapping_source"] == "suggested"
    assert body["recognized_columns"] >= 8

    reviewed = client.get(
        f"/api/v1/team/job-intake/batches/{body['id']}/items",
        headers=headers("manager-a"),
    )
    assert reviewed.status_code == 200
    items = reviewed.json()["items"]
    assert items[0]["normalized_job"]["title"] == "Contract PT - Maternity Leave Coverage"
    assert items[0]["normalized_job"]["facility"] == "The Terraces at San Joaquin Gardens"


def test_recruiter_can_read_own_weekly_progress(client, headers):
    saved = client.put(
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
    assert saved.status_code == 200
    response = client.get(
        f"/api/v1/team/recruiters/{idn(10)}/weekly-goals?week_start=2026-10-05",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["targets"]["submissions"] == 12
    assert body["actuals"]["submissions"] == 0


def test_recruiter_cannot_read_another_recruiters_weekly_progress(client, headers):
    response = client.get(
        f"/api/v1/team/recruiters/{idn(11)}/weekly-goals?week_start=2026-10-05",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 403


def publication_payload():
    return {
        "team_id": idn(30),
        "job_id": idn(200),
        "intake_item_id": None,
        "source_snapshot": {
            "title": "Contract PT - Maternity Leave Coverage",
            "city": "Fresno",
            "state": "CA",
            "bill_rate": 85,
        },
        "enhanced_snapshot": {
            "public_title": "Physical Therapist Travel Contract - Fresno, CA",
            "summary": "Medlivo is seeking a Physical Therapist in Fresno, California.",
            "sections": [
                {
                    "key": "overview",
                    "heading": "About the Opportunity",
                    "content": "Medlivo is seeking a Physical Therapist in Fresno, California.",
                    "provenance": "medlivo_standard",
                    "requires_confirmation": False,
                }
            ],
            "public_fields": {"city": "Fresno", "state": "CA"},
            "internal_fields": {"bill_rate": 85},
        },
        "quality_score": {
            "overall": 92,
            "core_data": 95,
            "matching_readiness": 95,
            "publishing_readiness": 90,
            "missing_fields": [],
            "warnings": [],
        },
        "readiness": "ready_to_publish",
    }


def test_manager_approves_recruiting_before_website(client, headers):
    created = client.post(
        "/api/v1/team/job-publications",
        headers=headers("manager-a"),
        json=publication_payload(),
    )
    assert created.status_code == 201
    publication = created.json()

    premature = client.post(
        f"/api/v1/team/job-publications/{publication['id']}/decision",
        headers=headers("manager-a"),
        json={
            "target": "website",
            "decision": "approved",
            "expected_version": publication["version"],
        },
    )
    assert premature.status_code == 422

    recruiting = client.post(
        f"/api/v1/team/job-publications/{publication['id']}/decision",
        headers=headers("manager-a"),
        json={
            "target": "recruiting",
            "decision": "approved",
            "expected_version": publication["version"],
        },
    )
    assert recruiting.status_code == 200
    assert recruiting.json()["recruiting_status"] == "approved"

    website = client.post(
        f"/api/v1/team/job-publications/{publication['id']}/decision",
        headers=headers("manager-a"),
        json={
            "target": "website",
            "decision": "approved",
            "expected_version": recruiting.json()["version"],
        },
    )
    assert website.status_code == 200
    assert website.json()["website_status"] == "approved"

    detail = client.get(
        f"/api/v1/team/job-publications/{publication['id']}",
        headers=headers("manager-a"),
    )
    assert detail.status_code == 200
    actions = [item["action"] for item in detail.json()["history"]]
    assert actions == ["draft.created", "recruiting.approved", "website.approved"]


def test_website_cannot_approve_job_that_is_not_publish_ready(client, headers):
    payload = publication_payload()
    payload["readiness"] = "manager_review"
    payload["quality_score"]["warnings"] = ["Confirm requirements"]
    created = client.post(
        "/api/v1/team/job-publications",
        headers=headers("manager-a"),
        json=payload,
    )
    assert created.status_code == 201

    recruiting = client.post(
        f"/api/v1/team/job-publications/{created.json()['id']}/decision",
        headers=headers("manager-a"),
        json={"target": "recruiting", "decision": "approved", "expected_version": 1},
    )
    assert recruiting.status_code == 200

    website = client.post(
        f"/api/v1/team/job-publications/{created.json()['id']}/decision",
        headers=headers("manager-a"),
        json={"target": "website", "decision": "approved", "expected_version": 2},
    )
    assert website.status_code == 422


def test_recruiter_cannot_access_job_publication_approval(client, headers):
    response = client.get(
        "/api/v1/team/job-publications",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 403


def seed_match_queue(seeded):
    with seeded.begin() as conn:
        conn.execute(update(t.jobs).where(t.jobs.c.id == idn(200)).values(
            profession="Physical Therapist", specialty="Physical Therapy",
            division="Rehabilitation", city="Fresno", state="CA",
            start_date=date(2026, 11, 29), status="open", priority=9,
            owner_user_id=idn(10), normalized_payload={"setting": "SNF"},
        ))
        conn.execute(update(t.jobs).where(t.jobs.c.id == idn(202)).values(
            profession="Registered Nurse", specialty="ICU",
            division="Nursing & Allied", city="Seattle", state="WA",
            start_date=date(2026, 12, 1), status="open", priority=10,
            owner_user_id=idn(15), normalized_payload={"shift": "Nights"},
        ))
        conn.execute(update(t.candidates).where(t.candidates.c.id == idn(300)).values(
            primary_email="candidate@example.test", profession="Physical Therapist",
            specialty="Physical Therapy", city="Fresno", state="CA",
            lifecycle_status="active", profile_freshness=95,
            canonical_profile={"matching_readiness": 95},
        ))
        conn.execute(insert(t.job_source_records).values(
            id=idn(960), tenant_id=idn(1), job_id=idn(200),
            source_system="jobdiva", source_id="JD-PT-200", source_status="open",
            source_updated_at=now(), raw_payload={},
        ))
        conn.execute(insert(t.candidate_source_records).values(
            id=idn(961), tenant_id=idn(1), candidate_id=idn(300),
            source_system="jobdiva", source_id="JD-CAND-300",
            source_updated_at=now(), raw_payload={},
        ))
        conn.execute(insert(t.matches).values(
            id=idn(962), tenant_id=idn(1), job_id=idn(200), candidate_id=idn(300),
            overall_score=9.4, status="shortlisted", rules_version="phase1-v1",
            explanation={
                "strengths": ["Exact profession match", "Active required-state license found"],
                "gaps": ["Availability has not been confirmed"],
            },
            created_at=now(), updated_at=now(),
        ))


def test_recruiter_match_queue_shows_owned_jobs_and_explainable_matches(client, headers, seeded):
    seed_match_queue(seeded)
    response = client.get(
        "/api/v1/team/work-queue?limit=25&matches_per_job=5",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source_of_record"] == "jobdiva"
    assert body["read_only"] is True
    assert len(body["items"]) == 1
    job = body["items"][0]
    assert job["jobdiva_job_id"] == "JD-PT-200"
    assert job["title"] == "Synthetic Physical Therapist"
    assert job["priority"] == 9
    assert job["match_readiness"]["status"] in {"ready", "needs_review", "limited_data"}
    assert len(job["match_readiness"]["checks"]) == 5
    assert job["evaluation_summary"]["evaluated_count"] == 1
    assert job["evaluation_summary"]["eligible_count"] == 1
    assert job["evaluation_summary"]["excluded_count"] == 0
    assert job["owner_name"] == "Synthetic recruiter-a"
    assert job["matches"][0]["score"] == 9.4
    assert job["matches"][0]["jobdiva_candidate_id"] == "JD-CAND-300"
    assert "Exact profession match" in job["matches"][0]["strengths"]


def test_manager_match_queue_is_limited_to_managed_team(client, headers, seeded):
    seed_match_queue(seeded)
    response = client.get(
        "/api/v1/team/work-queue",
        headers=headers("manager-a"),
    )
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["items"]]
    assert "Synthetic Physical Therapist" in titles
    assert "Synthetic Registered Nurse" not in titles


def test_recruiter_does_not_see_other_recruiters_jobs_in_match_queue(client, headers, seeded):
    seed_match_queue(seeded)
    response = client.get(
        "/api/v1/team/work-queue",
        headers=headers("recruiter-other"),
    )
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["items"]]
    assert titles == ["Synthetic Registered Nurse"]


def seed_candidate_best_jobs(seeded):
    seed_match_queue(seeded)
    with seeded.begin() as conn:
        conn.execute(update(t.jobs).where(t.jobs.c.id == idn(201)).values(
            profession="Physical Therapist", specialty="Rehab",
            division="Rehabilitation", city="Sacramento", state="CA",
            start_date=date(2026, 12, 15), status="open", priority=6,
            owner_user_id=idn(11), normalized_payload={"setting": "Outpatient"},
        ))
        conn.execute(insert(t.job_source_records).values(
            id=idn(963), tenant_id=idn(1), job_id=idn(201),
            source_system="jobdiva", source_id="JD-PT-201", source_status="open",
            source_updated_at=now(), raw_payload={},
        ))
        conn.execute(insert(t.matches).values(
            id=idn(964), tenant_id=idn(1), job_id=idn(201), candidate_id=idn(300),
            overall_score=8.7, status="shortlisted", rules_version="deterministic-v1",
            explanation={
                "eligible": True,
                "gates": [{"key": "profession", "passed": True, "reason": "Profession matches Physical Therapist"}],
                "strengths": ["Exact profession match"],
                "gaps": ["Care-setting experience not confirmed"],
            },
            created_at=now(), updated_at=now(),
        ))
        conn.execute(insert(t.matches).values(
            id=idn(965), tenant_id=idn(1), job_id=idn(202), candidate_id=idn(300),
            overall_score=0, status="excluded", rules_version="deterministic-v1",
            explanation={
                "eligible": False,
                "gates": [{"key": "profession", "passed": False, "reason": "Requires profession Registered Nurse"}],
                "strengths": [],
                "gaps": ["Requires profession Registered Nurse"],
            },
            created_at=now(), updated_at=now(),
        ))


def test_recruiter_match_queue_separates_assigned_and_division_opportunities(client, headers, seeded):
    seed_candidate_best_jobs(seeded)
    response = client.get(
        "/api/v1/team/work-queue?limit=25&matches_per_job=5",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["division_scope"] == "Rehabilitation"
    by_id = {item["job_id"]: item for item in body["items"]}
    assert by_id[idn(200)]["work_priority"] == "priority_1"
    assert by_id[idn(201)]["work_priority"] == "priority_2"
    assert [item["job_id"] for item in body["items"][:2]] == [idn(200), idn(201)]


def test_daily_priorities_include_same_division_priority_two_matches(client, headers, seeded):
    seed_candidate_best_jobs(seeded)
    response = client.get(
        "/api/v1/team/daily-priorities?limit=10",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 200
    body = response.json()
    matches = [item for item in body["items"] if item["type"] == "match_review"]
    by_job = {item["job_id"]: item for item in matches}
    assert by_job[idn(200)]["work_priority"] == "priority_1"
    assert by_job[idn(201)]["work_priority"] == "priority_2"
    assert body["totals"]["priority_1_matches"] == 1
    assert body["totals"]["priority_2_matches"] == 1


def test_candidate_best_jobs_returns_ranked_current_matches(client, headers, seeded):
    seed_candidate_best_jobs(seeded)
    response = client.get(
        f"/api/v1/team/candidates/{idn(300)}/best-jobs?limit=20",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["read_only"] is True
    assert body["source_of_record"] == "jobdiva"
    assert body["candidate"]["id"] == idn(300)
    assert body["excluded_count"] == 1
    assert [item["job_id"] for item in body["items"]] == [idn(200), idn(201)]
    assert body["items"][0]["score"] == 9.4
    assert body["items"][0]["jobdiva_job_id"] == "JD-PT-200"
    assert body["items"][1]["jobdiva_job_id"] == "JD-PT-201"
    assert body["items"][1]["gates"][0]["passed"] is True


def test_candidate_best_jobs_blocks_other_recruiter_owner(client, headers, seeded):
    seed_candidate_best_jobs(seeded)
    response = client.get(
        f"/api/v1/team/candidates/{idn(300)}/best-jobs",
        headers=headers("recruiter-other"),
    )
    assert response.status_code == 404


def test_candidate_best_jobs_allows_managed_team_manager(client, headers, seeded):
    seed_candidate_best_jobs(seeded)
    response = client.get(
        f"/api/v1/team/candidates/{idn(300)}/best-jobs",
        headers=headers("manager-a"),
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["title"] == "Synthetic Physical Therapist"


def test_candidate_best_jobs_hides_foreign_tenant_candidate(client, headers, seeded):
    response = client.get(
        f"/api/v1/team/candidates/{idn(303)}/best-jobs",
        headers=headers("admin-a"),
    )
    assert response.status_code == 404


def test_recruiter_can_save_match_quality_feedback(client, headers, seeded):
    seed_match_queue(seeded)
    response = client.post(
        f"/api/v1/team/matches/{idn(962)}/feedback",
        headers=headers("recruiter-a"),
        json={"feedback_code": "strong_match", "notes": "Synthetic pilot feedback"},
    )
    assert response.status_code == 200
    assert response.json()["feedback_code"] == "strong_match"

    with seeded.begin() as conn:
        row = conn.execute(select(t.match_feedback).where(
            t.match_feedback.c.tenant_id == idn(1),
            t.match_feedback.c.match_id == idn(962),
            t.match_feedback.c.recruiter_user_id == idn(10),
        )).mappings().first()
    assert row["feedback_code"] == "strong_match"


def test_negative_match_feedback_requires_structured_reason(client, headers, seeded):
    seed_match_queue(seeded)
    url = f"/api/v1/team/matches/{idn(962)}/feedback"

    missing = client.post(
        url,
        headers=headers("recruiter-a"),
        json={"feedback_code": "not_a_match"},
    )
    assert missing.status_code == 422

    saved = client.post(
        url,
        headers=headers("recruiter-a"),
        json={"feedback_code": "not_a_match", "reason_code": "license"},
    )
    assert saved.status_code == 200
    assert saved.json()["reason_code"] == "license"


def test_recruiter_cannot_rate_another_recruiters_match(client, headers, seeded):
    seed_match_queue(seeded)
    response = client.post(
        f"/api/v1/team/matches/{idn(962)}/feedback",
        headers=headers("recruiter-other"),
        json={"feedback_code": "not_a_match", "reason_code": "license"},
    )
    assert response.status_code == 403


def test_manager_match_quality_summary_uses_managed_team_feedback(client, headers, seeded):
    seed_match_queue(seeded)
    with seeded.begin() as conn:
        conn.execute(insert(t.match_feedback), [
            {
                "id": idn(970), "tenant_id": idn(1), "match_id": idn(962),
                "recruiter_user_id": idn(10), "feedback_code": "strong_match",
                "reason_code": None, "notes": None, "created_at": now(),
            },
        ])
        conn.execute(insert(t.matches).values(
            id=idn(971), tenant_id=idn(1), job_id=idn(202), candidate_id=idn(302),
            overall_score=9.2, status="shortlisted", rules_version="deterministic-v1",
            explanation={"strengths": ["Synthetic"], "gaps": []},
            created_at=now(), updated_at=now(),
        ))
        conn.execute(insert(t.match_feedback).values(
            id=idn(972), tenant_id=idn(1), match_id=idn(971),
            recruiter_user_id=idn(15), feedback_code="not_a_match",
            reason_code="specialty", notes=None, created_at=now(),
        ))

    response = client.get(
        "/api/v1/team/manager/match-quality",
        headers=headers("manager-a"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["feedback_count"] == 1
    band = next(item for item in body["score_bands"] if item["key"] == "9.0+")
    assert band["total"] == 1
    assert band["positive"] == 1
    assert band["agreement_rate"] == 100.0
    assert body["pilot_target"]["minimum_feedback"] == 100


def test_manager_match_quality_reports_negative_reasons_in_scope(client, headers, seeded):
    seed_match_queue(seeded)
    with seeded.begin() as conn:
        conn.execute(insert(t.match_feedback), {
            "id": idn(973), "tenant_id": idn(1), "match_id": idn(962),
            "recruiter_user_id": idn(10), "feedback_code": "weak_match",
            "reason_code": "availability", "notes": None, "created_at": now(),
        })

    response = client.get(
        "/api/v1/team/manager/match-quality",
        headers=headers("manager-a"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["negative_reasons"] == [{"key": "availability", "count": 1}]


def test_recruiter_cannot_access_manager_match_quality_summary(client, headers, seeded):
    response = client.get(
        "/api/v1/team/manager/match-quality",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 403


def test_daily_priorities_puts_followups_before_unreviewed_matches(client, headers, seeded):
    seed_match_queue(seeded)
    overdue = now() - timedelta(hours=2)
    soon = now() + timedelta(hours=4)
    with seeded.begin() as conn:
        conn.execute(insert(t.tasks), [
            {
                "id": idn(980), "tenant_id": idn(1), "case_id": idn(100),
                "created_by": idn(10), "title": "Call candidate back",
                "status": "open", "due_at": overdue, "version": 1,
                "created_at": now(), "updated_at": now(),
            },
            {
                "id": idn(981), "tenant_id": idn(1), "case_id": idn(100),
                "created_by": idn(10), "title": "Confirm availability",
                "status": "open", "due_at": soon, "version": 1,
                "created_at": now(), "updated_at": now(),
            },
        ])

    response = client.get(
        "/api/v1/team/daily-priorities?limit=10",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["read_only"] is True
    assert body["source_of_record"] == "jobdiva"
    assert body["totals"]["overdue_followups"] == 1
    assert body["totals"]["due_soon_followups"] == 1
    assert body["totals"]["match_reviews"] == 1
    assert [item["type"] for item in body["items"][:3]] == [
        "follow_up", "follow_up", "match_review",
    ]
    assert body["items"][0]["urgency"] == "overdue"
    assert body["items"][2]["score"] == 9.4


def test_daily_priorities_excludes_other_recruiter_work(client, headers, seeded):
    seed_match_queue(seeded)
    with seeded.begin() as conn:
        conn.execute(insert(t.tasks).values(
            id=idn(982), tenant_id=idn(1), case_id=idn(102),
            created_by=idn(15), title="Other recruiter follow-up",
            status="open", due_at=now() - timedelta(hours=1), version=1,
            created_at=now(), updated_at=now(),
        ))

    response = client.get(
        "/api/v1/team/daily-priorities",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["items"]]
    assert "Other recruiter follow-up" not in titles
    assert "Synthetic Candidate Three" not in titles


def test_daily_priorities_hides_already_reviewed_match(client, headers, seeded):
    seed_match_queue(seeded)
    with seeded.begin() as conn:
        conn.execute(insert(t.match_feedback).values(
            id=idn(983), tenant_id=idn(1), match_id=idn(962),
            recruiter_user_id=idn(10), feedback_code="strong_match",
            reason_code=None, notes=None, created_at=now(),
        ))

    response = client.get(
        "/api/v1/team/daily-priorities",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 200
    assert not any(item["type"] == "match_review" for item in response.json()["items"])


def test_manager_cannot_use_recruiter_daily_priorities(client, headers):
    response = client.get(
        "/api/v1/team/daily-priorities",
        headers=headers("manager-a"),
    )
    assert response.status_code == 403


def test_recruiter_dashboard_combines_goals_actuals_and_workload(client, headers, seeded):
    seed_match_queue(seeded)
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
            week_start=date(2026, 10, 5), submissions_actual=9, interviews_actual=4,
            closures_actual=1, offers_actual=2, starts_actual=1, qualified_actual=17,
            responses_actual=28, source_breakdown={"jobdiva": True, "platform": True},
            generated_at=now(),
        ))
        conn.execute(insert(t.tasks).values(
            id=idn(990), tenant_id=idn(1), case_id=idn(100), created_by=idn(10),
            title="Overdue recruiter follow-up", status="open",
            due_at=now() - timedelta(hours=2), version=1,
            created_at=now(), updated_at=now(),
        ))

    response = client.get(
        "/api/v1/team/recruiter/dashboard?week_start=2026-10-05",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["targets"]["submissions"] == 12
    assert body["actuals"]["submissions"] == 9
    assert body["workload"]["owned_work_items"] == 1
    assert body["workload"]["open_followups"] == 1
    assert body["workload"]["overdue_followups"] == 1
    assert body["workload"]["active_priority_jobs"] == 1
    assert body["workload"]["unreviewed_matches"] == 1
    assert body["read_only"] is True
    assert body["source_of_record"] == "jobdiva"


def test_manager_cannot_use_recruiter_dashboard(client, headers):
    response = client.get(
        "/api/v1/team/recruiter/dashboard?week_start=2026-10-05",
        headers=headers("manager-a"),
    )
    assert response.status_code == 403


def test_recruiter_dashboard_requires_monday(client, headers):
    response = client.get(
        "/api/v1/team/recruiter/dashboard?week_start=2026-10-06",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 422


def test_match_queue_returns_current_recruiter_feedback_state(client, headers, seeded):
    seed_match_queue(seeded)
    with seeded.begin() as conn:
        conn.execute(insert(t.match_feedback).values(
            id=idn(991), tenant_id=idn(1), match_id=idn(962),
            recruiter_user_id=idn(10), feedback_code="good_match",
            reason_code=None, notes=None, created_at=now(),
        ))
    response = client.get(
        "/api/v1/team/work-queue?limit=25&matches_per_job=5",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 200
    match = response.json()["items"][0]["matches"][0]
    assert match["my_feedback_code"] == "good_match"
    assert match["my_feedback_reason"] is None


def test_recruiter_followups_lists_only_owned_tasks_and_overdue_first(client, headers, seeded):
    with seeded.begin() as conn:
        conn.execute(insert(t.tasks), [
            {
                "id": idn(992), "tenant_id": idn(1), "case_id": idn(100),
                "created_by": idn(10), "title": "Overdue owned follow-up",
                "status": "open", "due_at": now() - timedelta(hours=2), "version": 1,
                "created_at": now(), "updated_at": now(),
            },
            {
                "id": idn(993), "tenant_id": idn(1), "case_id": idn(100),
                "created_by": idn(10), "title": "Future owned follow-up",
                "status": "open", "due_at": now() + timedelta(days=2), "version": 1,
                "created_at": now(), "updated_at": now(),
            },
            {
                "id": idn(994), "tenant_id": idn(1), "case_id": idn(102),
                "created_by": idn(15), "title": "Other recruiter follow-up",
                "status": "open", "due_at": now() - timedelta(days=1), "version": 1,
                "created_at": now(), "updated_at": now(),
            },
        ])
    response = client.get(
        "/api/v1/team/recruiter/follow-ups?status=open&limit=100",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["title"] for item in items] == [
        "Overdue owned follow-up", "Future owned follow-up",
    ]
    assert items[0]["is_overdue"] is True
    assert items[1]["is_overdue"] is False


def test_recruiter_followups_can_filter_completed(client, headers, seeded):
    with seeded.begin() as conn:
        conn.execute(insert(t.tasks).values(
            id=idn(995), tenant_id=idn(1), case_id=idn(100),
            created_by=idn(10), title="Completed owned follow-up",
            status="done", due_at=now() - timedelta(days=1), version=2,
            created_at=now(), updated_at=now(),
        ))
    response = client.get(
        "/api/v1/team/recruiter/follow-ups?status=done",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 200
    assert [item["title"] for item in response.json()["items"]] == ["Completed owned follow-up"]


def test_manager_cannot_use_recruiter_followups(client, headers):
    response = client.get(
        "/api/v1/team/recruiter/follow-ups",
        headers=headers("manager-a"),
    )
    assert response.status_code == 403


def test_candidate_360_combines_jobdiva_credentials_evidence_validation_and_best_jobs(client, headers, seeded):
    seed_candidate_best_jobs(seeded)
    with seeded.begin() as conn:
        conn.execute(update(t.candidate_source_records).where(
            t.candidate_source_records.c.id == idn(961)
        ).values(enriched_at=now(), enrichment_version="candidate-intelligence-v1"))
        conn.execute(insert(t.candidate_licenses).values(
            id=idn(1100), tenant_id=idn(1), candidate_id=idn(300),
            license_type="PT", state="CA", license_number="SYNTHETIC",
            status="active", verification_status="verified", source_system="jobdiva",
            source_reference="LIC-1", raw_payload={}, created_at=now(), updated_at=now(),
        ))
        conn.execute(insert(t.candidate_certifications).values(
            id=idn(1101), tenant_id=idn(1), candidate_id=idn(300),
            certification_key="bls", certification_name="BLS", status="active",
            verification_status="verified", source_system="jobdiva",
            source_reference="CERT-1", raw_payload={}, created_at=now(), updated_at=now(),
        ))
        conn.execute(insert(t.candidate_evidence).values(
            id=idn(1102), tenant_id=idn(1), candidate_id=idn(300),
            fact_key="care_setting", fact_value=["skilled_nursing"], source_type="resume",
            source_reference="resume-line-12", confidence=95, is_verified=False,
            created_at=now(), updated_at=now(),
        ))
        conn.execute(insert(t.resume_versions).values(
            id=idn(1103), tenant_id=idn(1), candidate_id=idn(300),
            source_record_id=idn(961), source_resume_id="RESUME-1",
            parsed_payload={"experience_years": 6}, is_primary=True,
            created_at=now(), updated_at=now(),
        ))
        conn.execute(insert(t.qualifications).values(
            id=idn(1104), tenant_id=idn(1), candidate_id=idn(300), job_id=idn(200),
            status="information_missing", summary="Confirm travel availability",
            created_at=now(),
        ))
        conn.execute(insert(t.qualification_answers).values(
            id=idn(1105), tenant_id=idn(1), qualification_id=idn(1104),
            question_key="travel_willingness", answer={"value": "unknown"},
            confirmed=False, created_at=now(),
        ))

    response = client.get(
        f"/api/v1/team/candidates/{idn(300)}",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"]["source_id"] == "JD-CAND-300"
    assert body["source"]["enrichment_version"] == "candidate-intelligence-v1"
    assert body["owner"]["owner_name"] == "Synthetic recruiter-a"
    assert body["owner"]["division"] == "Rehabilitation"
    assert body["readiness"]["status"] in {"review", "information_missing"}
    assert body["readiness"]["resume_count"] == 1
    assert body["readiness"]["verified_credential_count"] == 2
    assert body["match_summary"]["strong"] == 1
    assert body["match_summary"]["good"] == 1
    assert body["licenses"][0]["license_type"] == "PT"
    assert body["certifications"][0]["certification_key"] == "bls"
    assert body["evidence"][0]["fact_key"] == "care_setting"
    assert body["resumes"][0]["source_resume_id"] == "RESUME-1"
    assert body["validation"]["status"] == "information_missing"
    assert body["validation"]["answers"][0]["question_key"] == "travel_willingness"
    assert body["best_jobs"][0]["jobdiva_job_id"] == "JD-PT-200"


def test_job_360_combines_source_requirements_matches_and_exclusions(client, headers, seeded):
    seed_candidate_best_jobs(seeded)
    with seeded.begin() as conn:
        conn.execute(update(t.job_source_records).where(
            t.job_source_records.c.id == idn(960)
        ).values(enriched_at=now(), enrichment_version="job-intelligence-v1"))
        conn.execute(insert(t.job_requirements), [
            {
                "id": idn(1110), "tenant_id": idn(1), "job_id": idn(200),
                "requirement_type": "profession", "canonical_key": "profession",
                "value": {"value": "Physical Therapist"}, "is_hard_gate": True,
                "source_evidence": {"provenance": "source_confirmed"},
                "rules_version": "phase1-v1", "created_at": now(),
            },
            {
                "id": idn(1111), "tenant_id": idn(1), "job_id": idn(200),
                "requirement_type": "care_setting", "canonical_key": "care_setting",
                "value": {"value": "skilled_nursing"}, "is_hard_gate": False,
                "weight": 1.25, "source_evidence": {"provenance": "source_confirmed"},
                "rules_version": "phase1-v1", "created_at": now(),
            },
        ])
        conn.execute(insert(t.match_exclusions).values(
            id=idn(1112), tenant_id=idn(1), job_id=idn(200), candidate_id=idn(302),
            reason_code="profession", reason_detail="Requires Physical Therapist",
            overridden=False, created_at=now(),
        ))

    response = client.get(
        f"/api/v1/team/jobs/{idn(200)}",
        headers=headers("recruiter-a"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"]["source_id"] == "JD-PT-200"
    assert body["source"]["enrichment_version"] == "job-intelligence-v1"
    assert body["match_readiness"]["status"] == "ready"
    assert body["match_readiness"]["requirement_count"] == 2
    assert body["match_readiness"]["hard_gate_count"] == 1
    assert body["match_summary"]["strong"] == 1
    assert body["operational"]["job_priority"] == "standard"
    assert len(body["requirements"]) == 2
    assert body["hard_gates"][0]["canonical_key"] == "profession"
    assert body["preferences"][0]["canonical_key"] == "care_setting"
    assert body["best_candidates"][0]["jobdiva_candidate_id"] == "JD-CAND-300"
    assert body["exclusions"][0]["reason_code"] == "profession"


def test_delivery_manager_sets_hot_job_and_audit(client, headers, seeded):
    with seeded.begin() as conn:
        conn.execute(update(t.jobs).where(t.jobs.c.id == idn(200)).values(
            division="Rehabilitation", status="open"
        ))

    response = client.put(
        f"/api/v1/team/jobs/{idn(200)}/operational",
        headers=headers("manager-a"),
        json={
            "client_priority": "high",
            "job_priority": "hot",
            "priority_reason": "Client requested immediate coverage",
            "manager_note": "Focus today",
            "next_action": "Submit qualified candidates",
            "due_at": "2026-10-10T17:00:00-07:00",
            "operational_status": "active",
            "expected_version": 0,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["job_priority"] == "hot"
    assert body["client_priority"] == "high"
    assert body["team_id"] == idn(30)
    assert body["version"] == 1

    job360 = client.get(
        f"/api/v1/team/jobs/{idn(200)}",
        headers=headers("manager-a"),
    )
    assert job360.status_code == 200
    assert job360.json()["operational"]["job_priority"] == "hot"
    assert job360.json()["operational"]["next_action"] == "Submit qualified candidates"

    audit = client.get(
        f"/api/v1/team/manager/operational-audit?object_type=job&object_id={idn(200)}",
        headers=headers("manager-a"),
    )
    assert audit.status_code == 200
    assert audit.json()["items"][0]["action"] == "job.operational.updated"


def test_recruiter_cannot_set_hot_job(client, headers, seeded):
    with seeded.begin() as conn:
        conn.execute(update(t.jobs).where(t.jobs.c.id == idn(200)).values(
            division="Rehabilitation", status="open"
        ))
    response = client.put(
        f"/api/v1/team/jobs/{idn(200)}/operational",
        headers=headers("recruiter-a"),
        json={
            "client_priority": "normal",
            "job_priority": "hot",
            "priority_reason": "Recruiter cannot promote priority",
            "operational_status": "active",
            "expected_version": 0,
        },
    )
    assert response.status_code == 403


def test_delivery_manager_assigns_job_and_preserves_ownership_history(client, headers, seeded):
    with seeded.begin() as conn:
        conn.execute(update(t.jobs).where(t.jobs.c.id == idn(200)).values(
            division="Rehabilitation", status="open"
        ))

    response = client.put(
        f"/api/v1/team/jobs/{idn(200)}/assignment",
        headers=headers("manager-a"),
        json={
            "team_id": idn(30),
            "recruiter_user_id": idn(11),
            "reason": "Balance priority workload across the rehab team",
            "expected_version": 0,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["recruiter_user_id"] == idn(11)
    assert body["team_id"] == idn(30)
    assert body["version"] == 1

    with seeded.begin() as conn:
        history = conn.execute(select(t.job_ownership_history).where(
            t.job_ownership_history.c.tenant_id == idn(1),
            t.job_ownership_history.c.job_id == idn(200),
        )).mappings().all()
    assert len(history) == 1
    assert history[0]["new_owner_user_id"] == idn(11)
    assert history[0]["changed_by"] == idn(12)


def test_delivery_manager_cannot_assign_recruiter_from_other_team(client, headers, seeded):
    with seeded.begin() as conn:
        conn.execute(update(t.jobs).where(t.jobs.c.id == idn(200)).values(
            division="Rehabilitation", status="open"
        ))
    response = client.put(
        f"/api/v1/team/jobs/{idn(200)}/assignment",
        headers=headers("manager-a"),
        json={
            "team_id": idn(30),
            "recruiter_user_id": idn(15),
            "reason": "Attempt cross-team assignment should fail",
            "expected_version": 0,
        },
    )
    assert response.status_code == 422


def test_operational_overlay_uses_optimistic_concurrency(client, headers, seeded):
    with seeded.begin() as conn:
        conn.execute(update(t.jobs).where(t.jobs.c.id == idn(200)).values(
            division="Rehabilitation", status="open"
        ))

    first = client.put(
        f"/api/v1/team/jobs/{idn(200)}/operational",
        headers=headers("manager-a"),
        json={
            "client_priority": "high",
            "job_priority": "priority",
            "priority_reason": "Priority customer",
            "operational_status": "active",
            "expected_version": 0,
        },
    )
    assert first.status_code == 200

    stale = client.put(
        f"/api/v1/team/jobs/{idn(200)}/operational",
        headers=headers("manager-a"),
        json={
            "client_priority": "high",
            "job_priority": "hot",
            "priority_reason": "Stale update",
            "operational_status": "active",
            "expected_version": 0,
        },
    )
    assert stale.status_code == 409


def test_delivery_manager_approves_direct_intake_without_inventing_bill_rate(client, headers):
    created = client.post(
        "/api/v1/team/job-intake/batches",
        headers=headers("manager-a"),
        json={
            "customer_name": "Synthetic Rehab Customer",
            "division": "Rehabilitation",
            "source_filename": "direct-jobs.xlsx",
            "mapping": {
                "Title": "title",
                "State": "state",
                "Start": "start_date",
                "Hours": "hours_per_week",
            },
        },
    )
    assert created.status_code == 201
    batch_id = created.json()["id"]

    processed = client.post(
        f"/api/v1/team/job-intake/batches/{batch_id}/rows",
        headers=headers("manager-a"),
        json={"rows": [{
            "Title": "Travel Physical Therapist",
            "State": "WA",
            "Start": "2026-11-01",
            "Hours": 40,
        }]},
    )
    assert processed.status_code == 200

    items = client.get(
        f"/api/v1/team/job-intake/batches/{batch_id}/items",
        headers=headers("manager-a"),
    ).json()["items"]
    item_id = items[0]["id"]

    approved = client.post(
        f"/api/v1/team/job-intake/batches/{batch_id}/items/{item_id}/decision",
        headers=headers("manager-a"),
        json={
            "decision": "approved",
            "final_approved_values": {
                "title": "Travel Physical Therapist",
                "profession": "Physical Therapist",
                "specialty": "Physical Therapy",
                "city": "Seattle",
                "state": "WA",
                "start_date": "2026-11-01",
                "hours_per_week": 40
            },
            "bill_rate_state": "unknown",
            "recruiting_readiness": "ready",
            "commercial_readiness": "review",
            "reason": "Manager confirmed missing recruiting facts; commercial rate still pending",
        },
    )
    assert approved.status_code == 200
    body = approved.json()
    assert body["status"] == "approved"
    assert body["bill_rate_state"] == "unknown"
    assert body["recruiting_readiness"] == "ready"
    assert body["commercial_readiness"] == "review"
    assert "bill_rate" not in body["final_approved_values"]


def test_confirmed_bill_rate_requires_approved_value(client, headers):
    created = client.post(
        "/api/v1/team/job-intake/batches",
        headers=headers("manager-a"),
        json={
            "customer_name": "Synthetic Rehab Customer",
            "division": "Rehabilitation",
            "source_filename": "direct-jobs.xlsx",
            "mapping": {
                "Title": "title",
                "State": "state",
                "Start": "start_date",
                "Hours": "hours_per_week",
            },
        },
    )
    batch_id = created.json()["id"]
    client.post(
        f"/api/v1/team/job-intake/batches/{batch_id}/rows",
        headers=headers("manager-a"),
        json={"rows": [{
            "Title": "Travel Physical Therapist",
            "State": "WA",
            "Start": "2026-11-01",
            "Hours": 40,
        }]},
    )
    item_id = client.get(
        f"/api/v1/team/job-intake/batches/{batch_id}/items",
        headers=headers("manager-a"),
    ).json()["items"][0]["id"]

    response = client.post(
        f"/api/v1/team/job-intake/batches/{batch_id}/items/{item_id}/decision",
        headers=headers("manager-a"),
        json={
            "decision": "approved",
            "bill_rate_state": "confirmed",
            "recruiting_readiness": "ready",
            "commercial_readiness": "ready",
        },
    )
    assert response.status_code == 422


def test_intake_processing_persists_standardized_jd_readiness_and_provenance(client, headers, seeded):
    created = client.post(
        "/api/v1/team/job-intake/batches",
        headers=headers("manager-a"),
        json={
            "customer_name": "Synthetic Rehab Customer",
            "division": "Rehabilitation",
            "source_filename": "rehab-intelligence.xlsx",
            "mapping": {
                "Title": "title",
                "Profession": "profession",
                "Specialty": "specialty",
                "City": "city",
                "State": "state",
                "Start": "start_date",
                "Bill Rate": "bill_rate",
                "Hours": "hours_per_week",
                "Description": "description"
            },
        },
    )
    batch_id = created.json()["id"]
    processed = client.post(
        f"/api/v1/team/job-intake/batches/{batch_id}/rows",
        headers=headers("manager-a"),
        json={"rows": [{
            "Title": "Travel Physical Therapist",
            "Profession": "Physical Therapist",
            "Specialty": "Physical Therapy",
            "City": "Seattle",
            "State": "WA",
            "Start": "2026-11-01",
            "Bill Rate": 95,
            "Hours": 40,
            "Description": "Treat adult patients in the client's rehabilitation setting."
        }]},
    )
    assert processed.status_code == 200
    assert processed.json()["ready_count"] == 1

    items = client.get(
        f"/api/v1/team/job-intake/batches/{batch_id}/items",
        headers=headers("manager-a"),
    ).json()["items"]
    item = items[0]
    assert item["bill_rate_state"] == "confirmed"
    assert item["recruiting_readiness"] == "ready"
    assert item["commercial_readiness"] == "ready"
    assert item["standardized_internal_jd"]["job_title"] == "Travel Physical Therapist"
    assert item["standardized_internal_jd"]["source_description"].startswith("Treat adult patients")
    assert "patient-centered" not in str(item["standardized_internal_jd"]).lower()

    with seeded.begin() as conn:
        provenance = conn.execute(select(t.provenance_records).where(
            t.provenance_records.c.tenant_id == idn(1),
            t.provenance_records.c.object_type == "job_intake_item",
            t.provenance_records.c.object_id == item["id"],
        )).mappings().all()
    fields = {row["field_path"] for row in provenance}
    assert {"title", "profession", "specialty", "city", "state", "bill_rate"}.issubset(fields)


def test_manager_cannot_mark_incomplete_intake_recruiting_ready(client, headers):
    created = client.post(
        "/api/v1/team/job-intake/batches",
        headers=headers("manager-a"),
        json={
            "customer_name": "Synthetic Rehab Customer",
            "division": "Rehabilitation",
            "source_filename": "incomplete.xlsx",
            "mapping": {"Title": "title", "State": "state", "Start": "start_date"},
        },
    )
    batch_id = created.json()["id"]
    client.post(
        f"/api/v1/team/job-intake/batches/{batch_id}/rows",
        headers=headers("manager-a"),
        json={"rows": [{
            "Title": "Travel Physical Therapist",
            "State": "WA",
            "Start": "2026-11-01"
        }]},
    )
    item_id = client.get(
        f"/api/v1/team/job-intake/batches/{batch_id}/items",
        headers=headers("manager-a"),
    ).json()["items"][0]["id"]

    response = client.post(
        f"/api/v1/team/job-intake/batches/{batch_id}/items/{item_id}/decision",
        headers=headers("manager-a"),
        json={
            "decision": "approved",
            "bill_rate_state": "unknown",
            "recruiting_readiness": "ready",
            "commercial_readiness": "review"
        },
    )
    assert response.status_code == 422


def test_system_admin_profile_can_read_admin_console_endpoints(client, headers, seeded):
    with seeded.begin() as conn:
        conn.execute(insert(t.access_profiles).values(
            user_id=idn(12), tenant_id=idn(1), business_role="delivery_manager",
            system_admin=True, created_at=now(), updated_at=now(),
        ))

    for path in [
        "/api/v1/team/admin/users",
        "/api/v1/team/admin/teams",
        "/api/v1/team/admin/audit?limit=10",
    ]:
        response = client.get(path, headers=headers("manager-a"))
        assert response.status_code == 200, (path, response.text)


def test_job_intake_ai_draft_requires_human_review_and_preserves_provenance(seeded, verifier, headers):
    class FakeJobIntakeAI:
        def compose(self, context):
            assert context["source_description_present"] is False
            return JobIntakeAIResult(
                job_description="Provide physical therapy services consistent with the confirmed rehabilitation assignment and facility setting.",
                responsibilities=["Evaluate patients and provide therapy within the assigned care setting."],
                required_qualifications=["Physical Therapist professional background."],
                preferred_qualifications=[],
                schedule_summary=None,
                warnings=["Confirm any customer-specific productivity or documentation requirements."],
                provider="test_provider",
                model="test_model",
            )

    test_client = TestClient(build_app(
        WorkspaceStore(seeded, job_intake_ai=FakeJobIntakeAI()),
        verifier,
    ))
    created = test_client.post(
        "/api/v1/team/job-intake/batches",
        headers=headers("manager-a"),
        json={
            "customer_name": "Synthetic Rehab Customer",
            "division": "Rehabilitation",
            "source_filename": "missing-jd.xlsx",
            "mapping": {
                "Title": "title", "Profession": "profession", "Specialty": "specialty",
                "City": "city", "State": "state", "Start": "start_date"
            },
        },
    )
    assert created.status_code == 201
    batch_id = created.json()["id"]
    processed = test_client.post(
        f"/api/v1/team/job-intake/batches/{batch_id}/rows",
        headers=headers("manager-a"),
        json={"rows": [{
            "Title": "Contract PT", "Profession": "Physical Therapist",
            "Specialty": "Physical Therapy", "City": "Seattle", "State": "WA",
            "Start": "2026-11-01"
        }]},
    )
    assert processed.status_code == 200
    item = test_client.get(
        f"/api/v1/team/job-intake/batches/{batch_id}/items",
        headers=headers("manager-a"),
    ).json()["items"][0]
    assert item["ai_suggestions"] == []

    drafted = test_client.post(
        f"/api/v1/team/job-intake/batches/{batch_id}/items/{item['id']}/ai-draft",
        headers=headers("manager-a"),
        json={},
    )
    assert drafted.status_code == 200
    draft = drafted.json()["ai_suggestions"][0]
    assert draft["status"] == "ai_suggested"
    assert draft["job_description"].startswith("Provide physical therapy")
    assert drafted.json()["status"] != "approved"

    reviewed_text = draft["job_description"] + "\n\nResponsibilities\n• " + draft["responsibilities"][0]
    accepted = test_client.post(
        f"/api/v1/team/job-intake/batches/{batch_id}/items/{item['id']}/decision",
        headers=headers("manager-a"),
        json={
            "decision": "approved",
            "final_approved_values": {
                **item["normalized_job"],
                "description": reviewed_text,
            },
            "bill_rate_state": item["bill_rate_state"],
            "recruiting_readiness": item["recruiting_readiness"],
            "commercial_readiness": item["commercial_readiness"],
            "reason": "Manager reviewed and accepted AI JD",
        },
    )
    assert accepted.status_code == 200
    body = accepted.json()
    assert body["status"] == "approved"
    assert body["standardized_internal_jd"]["description_provenance"] == "human_approved_ai_draft"
    assert body["standardized_internal_jd"]["source_description"] == reviewed_text
    assert body["job_publication_id"]

    publications = test_client.get(
        "/api/v1/team/job-publications?limit=100",
        headers=headers("manager-a"),
    )
    assert publications.status_code == 200
    matching = [
        x for x in publications.json()["items"]
        if x["intake_item_id"] == item["id"]
    ]
    assert len(matching) == 1
    publication = matching[0]
    assert publication["recruiting_status"] == "pending"
    assert publication["website_status"] == "pending"
    assert publication["source_snapshot"]["description"] == reviewed_text
    reviewed_sections = [
        x for x in publication["enhanced_snapshot"]["sections"]
        if x["key"] == "reviewed_jd"
    ]
    assert reviewed_sections[0]["provenance"] == "human_approved_ai_draft"

    refreshed = test_client.get(
        f"/api/v1/team/job-intake/batches/{batch_id}/items",
        headers=headers("manager-a"),
    ).json()
    refreshed_item = refreshed["items"][0]
    assert refreshed_item["job_publication_id"] == publication["id"]
    assert refreshed["batch"]["ready_count"] == 1
    assert refreshed["batch"]["review_count"] == 0

    detail = test_client.get(
        f"/api/v1/team/job-publications/{publication['id']}",
        headers=headers("manager-a"),
    )
    assert detail.status_code == 200
    assert detail.json()["history"][0]["action"] == "draft.created"



def test_job_content_standards_are_versioned_and_active_version_replaces_matching_role(seeded, verifier, headers):
    test_client = TestClient(build_app(WorkspaceStore(seeded), verifier))
    payload = {
        "division": "Rehabilitation",
        "profession": "Physical Therapist",
        "specialty": "Physical Therapy",
        "care_setting": "Skilled Nursing",
        "display_title": "Physical Therapist",
        "status": "active",
        "content": {
            "candidate_intro": "Join Medlivo for a rehabilitation contract assignment.",
            "responsibilities": ["Evaluate patients and deliver skilled physical therapy services."],
            "required_qualifications": ["Physical Therapist professional background."],
            "preferred_qualifications": [],
            "licensure_certification": ["Active license as required for the assignment state."],
            "assignment_overview": None,
            "about_medlivo": None,
            "candidate_cta": "Apply to connect with a Medlivo recruiter.",
            "seo_title": None,
            "seo_description": None,
        },
    }
    first = test_client.post(
        "/api/v1/team/job-content-standards",
        headers=headers("manager-a"),
        json=payload,
    )
    assert first.status_code == 201
    assert first.json()["version"] == 1
    assert first.json()["status"] == "active"

    payload["content"]["candidate_intro"] = "Updated approved Medlivo PT introduction."
    second = test_client.post(
        "/api/v1/team/job-content-standards",
        headers=headers("manager-a"),
        json=payload,
    )
    assert second.status_code == 201
    assert second.json()["version"] == 2

    listed = test_client.get(
        "/api/v1/team/job-content-standards?division=Rehabilitation",
        headers=headers("manager-a"),
    )
    assert listed.status_code == 200
    matching = [
        item for item in listed.json()["items"]
        if item["profession"] == "Physical Therapist"
        and item["specialty"] == "Physical Therapy"
        and item["care_setting"] == "Skilled Nursing"
    ]
    assert len(matching) == 2
    assert [item["status"] for item in matching].count("active") == 1
    assert max(item["version"] for item in matching) == 2

    active = test_client.get(
        "/api/v1/team/job-content-standards/active"
        "?division=Rehabilitation&profession=Physical%20Therapist"
        "&specialty=Physical%20Therapy&care_setting=Skilled%20Nursing",
        headers=headers("manager-a"),
    )
    assert active.status_code == 200
    assert active.json()["version"] == 2
    assert active.json()["content"]["candidate_intro"].startswith("Updated approved")



def test_batch_jd_preparation_uses_active_medlivo_standard_and_flags_unmatched_roles(seeded, verifier, headers):
    test_client = TestClient(build_app(WorkspaceStore(seeded), verifier))

    standard = test_client.post(
        "/api/v1/team/job-content-standards",
        headers=headers("manager-a"),
        json={
            "division": "Rehabilitation",
            "profession": "Physical Therapist",
            "specialty": "Physical Therapy",
            "care_setting": None,
            "display_title": "Physical Therapist",
            "status": "active",
            "content": {
                "candidate_intro": "Medlivo is seeking a Physical Therapist for a contract assignment.",
                "responsibilities": ["Evaluate patients and provide skilled physical therapy services."],
                "required_qualifications": ["Physical Therapist professional background."],
                "preferred_qualifications": [],
                "licensure_certification": ["Active license as required for the assignment state."],
                "assignment_overview": None,
                "about_medlivo": None,
                "candidate_cta": "Apply to connect with a Medlivo recruiter.",
                "seo_title": None,
                "seo_description": None,
            },
        },
    )
    assert standard.status_code == 201

    created = test_client.post(
        "/api/v1/team/job-intake/batches",
        headers=headers("manager-a"),
        json={
            "customer_name": "Rockport",
            "division": "Rehabilitation",
            "source_filename": "multi-role.xlsx",
            "mapping": {
                "Title": "title", "Profession": "profession", "Specialty": "specialty",
                "City": "city", "State": "state", "Start": "start_date"
            },
        },
    )
    batch_id = created.json()["id"]
    processed = test_client.post(
        f"/api/v1/team/job-intake/batches/{batch_id}/rows",
        headers=headers("manager-a"),
        json={"rows": [
            {
                "Title": "Contract PT", "Profession": "Physical Therapist",
                "Specialty": "Physical Therapy", "City": "Seattle", "State": "WA",
                "Start": "2026-11-01"
            },
            {
                "Title": "Contract OT", "Profession": "Occupational Therapist",
                "Specialty": "Occupational Therapy", "City": "Tacoma", "State": "WA",
                "Start": "2026-11-08"
            },
        ]},
    )
    assert processed.status_code == 200

    prepared = test_client.post(
        f"/api/v1/team/job-intake/batches/{batch_id}/prepare-standards",
        headers=headers("manager-a"),
        json={},
    )
    assert prepared.status_code == 200
    body = prepared.json()
    assert body["prepared"] == 1
    assert len(body["missing_standard"]) == 1
    assert body["missing_standard"][0]["profession"] == "Occupational Therapist"
    assert body["human_approval_required"] is True

    refreshed = test_client.get(
        f"/api/v1/team/job-intake/batches/{batch_id}/items",
        headers=headers("manager-a"),
    ).json()["items"]
    pt = next(item for item in refreshed if item["normalized_job"]["profession"] == "Physical Therapist")
    draft = pt["ai_suggestions"][0]
    assert draft["provenance"] == "medlivo_standard"
    assert draft["standard_version"] == 1
    assert draft["job_description"].startswith("Medlivo is seeking")
    assert pt["status"] != "approved"
