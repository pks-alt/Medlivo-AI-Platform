from fastapi import APIRouter, HTTPException

from app.schemas.recruiting import CandidateProfile, DashboardSummary, JobDetail, JobListItem
from app.services.recruiting import get_candidate, get_dashboard, get_job, get_jobs

router = APIRouter(prefix="/api/v1", tags=["recruiting"])


@router.get("/dashboard", response_model=DashboardSummary)
async def dashboard() -> DashboardSummary:
    return await get_dashboard()


@router.get("/jobs", response_model=list[JobListItem])
async def jobs() -> list[JobListItem]:
    return await get_jobs()


@router.get("/jobs/{job_id}", response_model=JobDetail)
async def job(job_id: str) -> JobDetail:
    try:
        return await get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc


@router.get("/candidates/{candidate_id}", response_model=CandidateProfile)
async def candidate(candidate_id: str) -> CandidateProfile:
    try:
        return await get_candidate(candidate_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Candidate not found") from exc
