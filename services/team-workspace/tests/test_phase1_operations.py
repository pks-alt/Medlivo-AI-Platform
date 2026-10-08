from datetime import date
from uuid import uuid4
from io import BytesIO
from openpyxl import Workbook

from workspace_api import tables as t
from sqlalchemy import insert, update
from workspace_api.store import now


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
    assert summary["ready_count"] == 2
    assert summary["duplicate_count"] == 1
    assert summary["review_count"] == 1

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
    assert body["ready_count"] == 2
    assert body["review_count"] == 0
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
    assert response.status_code == 403


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
