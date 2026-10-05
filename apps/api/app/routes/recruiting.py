from fastapi import APIRouter

from app.schemas.recruiting import CandidateProfile, DashboardSummary, JobDetail, JobListItem
from app.services.mock_recruiting import CANDIDATE_PROFILE, DASHBOARD, JOB_DETAIL, JOBS

router = APIRouter(prefix="/api/v1", tags=["recruiting"])


@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard() -> DashboardSummary:
    return DASHBOARD


@router.get("/jobs", response_model=list[JobListItem])
async def list_jobs() -> list[JobListItem]:
    return JOBS


@router.get("/jobs/{job_id}", response_model=JobDetail)
async def get_job(job_id: str) -> JobDetail:
    if job_id != JOB_DETAIL.id:
        return JOB_DETAIL
    return JOB_DETAIL


@router.get("/candidates/{candidate_id}", response_model=CandidateProfile)
async def get_candidate(candidate_id: str) -> CandidateProfile:
    if candidate_id != CANDIDATE_PROFILE.id:
        return CANDIDATE_PROFILE
    return CANDIDATE_PROFILE
