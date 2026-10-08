from fastapi import APIRouter, Query

from app.schemas.integration import JobDivaSyncHealth
from app.services.integration import get_jobdiva_sync_health


router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])


@router.get("/jobdiva/health", response_model=JobDivaSyncHealth)
async def jobdiva_health(
    stale_after_minutes: int = Query(default=30, ge=5, le=1440),
) -> JobDivaSyncHealth:
    """Operational metadata only; never returns candidate/job payloads."""
    return await get_jobdiva_sync_health(
        stale_after_minutes=stale_after_minutes
    )
