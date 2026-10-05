from datetime import date

from app.schemas.recruiting import (
    CandidateMatch,
    CandidateProfile,
    DashboardSummary,
    JobDetail,
    JobListItem,
    MatchSignal,
)


DASHBOARD = DashboardSummary(
    submission_ready=7,
    interested_replies=12,
    jobs_at_risk=3,
    active_matching_jobs=32,
    qualified_today=21,
)

JOBS = [
    JobListItem(
        id="job-1",
        source_job_id="26-37123",
        title="Urologist",
        division="Locum Tenens",
        customer="Regional Health",
        location="Kearney, NE",
        status="matching",
        strong_matches=18,
        submission_ready=3,
        start_date=date(2026, 10, 19),
    ),
    JobListItem(
        id="job-2",
        source_job_id="26-31915",
        title="Occupational Therapist",
        division="Rehabilitation",
        customer="Axiom Rehab",
        location="Houston, TX",
        status="qualifying",
        strong_matches=14,
        submission_ready=2,
        start_date=date(2026, 10, 26),
    ),
    JobListItem(
        id="job-3",
        source_job_id="26-13176",
        title="Registered Nurse",
        division="Nursing & Allied",
        customer="Providence",
        location="Seattle, WA",
        status="needs_outreach",
        strong_matches=37,
        submission_ready=1,
        start_date=date(2026, 10, 20),
    ),
]

DANA_MATCH = CandidateMatch(
    id="candidate-1",
    name="Dr. Dana Patel",
    profession="Physician",
    specialty="Urology",
    location="Omaha, NE",
    overall_score=94,
    readiness_status="near_ready",
    signals=[
        MatchSignal(key="clinical", label="Clinical", status="good", value="98"),
        MatchSignal(key="license", label="License", status="good", value="Ready"),
        MatchSignal(key="availability", label="Availability", status="good", value="Oct 19"),
        MatchSignal(key="engagement", label="Engagement", status="good", value="Interested"),
    ],
    why_matched="Strong specialty alignment, Nebraska location, confirmed availability, and no current hard blocker.",
)

JOB_DETAIL = JobDetail(
    id="job-1",
    source_job_id="26-37123",
    title="Urologist",
    division="Locum Tenens",
    customer="Regional Health",
    location="Kearney, NE",
    status="matching",
    start_timing="ASAP",
    recruiter_owner="Rey Rivera",
    requirements={
        "profession": "Physician",
        "specialty": "Urology",
        "license": "NE active or ready before start",
        "availability": "Compatible with start timing",
    },
    hard_gates=[
        "Correct specialty",
        "Location/travel feasible",
        "License-ready",
        "Start-date compatible",
    ],
    candidate_matches=[DANA_MATCH],
)

CANDIDATE_PROFILE = CandidateProfile(
    id="candidate-1",
    name="Dr. Dana Patel",
    profession="Physician",
    specialty="Urology",
    location="Omaha, NE",
    travel_preference="Willing to travel",
    availability="Oct 19",
    license_readiness="Ready",
    overall_match=94,
    clinical_fit=98,
    engagement="Interested",
    owner="Rey Rivera",
    readiness_status="near_ready",
    evidence=[
        {"type": "Clinical", "value": "Recent urology experience aligns closely", "source": "Resume + normalized profile"},
        {"type": "Location", "value": "Nebraska-based candidate", "source": "Candidate profile"},
        {"type": "Availability", "value": "Available Oct 19", "source": "Candidate conversation"},
        {"type": "License", "value": "Ready for current start window", "source": "Credential profile"},
    ],
)
