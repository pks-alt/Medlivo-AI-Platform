from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response

from app.schemas.career import PublicJobDetail, PublicJobPage
from app.services.career import get_public_job, get_public_jobs


router = APIRouter(prefix="/api/v1/careers", tags=["careers"])


def _cache(response: Response) -> None:
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    response.headers["X-Content-Type-Options"] = "nosniff"


@router.get("/jobs", response_model=PublicJobPage)
async def jobs(
    response: Response,
    division: str | None = None,
    profession: str | None = Query(default=None, max_length=200),
    specialty: str | None = Query(default=None, max_length=200),
    state: str | None = Query(default=None, min_length=2, max_length=2),
    city: str | None = Query(default=None, max_length=120),
    after: UUID | None = None,
    limit: int = Query(default=24, ge=1, le=100),
) -> PublicJobPage:
    if division not in {None, "rehabilitation", "nursing_allied", "locum_tenens"}:
        raise HTTPException(422, "Unsupported division")
    if state:
        state = state.upper()
    result = await get_public_jobs(
        division=division,
        profession=profession,
        specialty=specialty,
        state=state,
        city=city,
        after=after,
        limit=limit,
    )
    _cache(response)
    return result


@router.get("/jobs/{job_id}", response_model=PublicJobDetail)
async def job(job_id: UUID, response: Response) -> PublicJobDetail:
    try:
        result = await get_public_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    _cache(response)
    return result
