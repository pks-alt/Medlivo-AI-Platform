from __future__ import annotations

from uuid import UUID

from app.repositories.career import CareerRepository
from app.schemas.career import PublicJobDetail, PublicJobPage


_repository = CareerRepository()


async def get_public_jobs(
    *,
    division: str | None = None,
    profession: str | None = None,
    specialty: str | None = None,
    state: str | None = None,
    city: str | None = None,
    after: UUID | None = None,
    limit: int = 24,
) -> PublicJobPage:
    return await _repository.list_jobs(
        division=division,
        profession=profession,
        specialty=specialty,
        state=state,
        city=city,
        after=after,
        limit=limit,
    )


async def get_public_job(job_id: UUID) -> PublicJobDetail:
    return await _repository.get_job(job_id)
