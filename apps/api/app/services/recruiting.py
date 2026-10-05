from app.core.settings import settings
from app.db.database import database_configured
from app.repositories.recruiting import RecruitingRepository
from app.schemas.recruiting import CandidateProfile, DashboardSummary, JobDetail, JobListItem
from app.services.mock_recruiting import CANDIDATE_PROFILE, DASHBOARD, JOB_DETAIL, JOBS


_repository = RecruitingRepository()


async def get_dashboard() -> DashboardSummary:
    if settings.use_mock_data or not database_configured():
        return DASHBOARD
    return await _repository.dashboard()


async def get_jobs() -> list[JobListItem]:
    if settings.use_mock_data or not database_configured():
        return JOBS
    return await _repository.jobs()


async def get_job(job_id: str) -> JobDetail:
    if settings.use_mock_data or not database_configured():
        return JOB_DETAIL
    return await _repository.job_detail(job_id)


async def get_candidate(candidate_id: str) -> CandidateProfile:
    if settings.use_mock_data or not database_configured():
        return CANDIDATE_PROFILE
    return await _repository.candidate_profile(candidate_id)
