from app.repositories.integration import IntegrationRepository
from app.schemas.integration import JobDivaSyncHealth


async def get_jobdiva_sync_health(*, stale_after_minutes: int = 30) -> JobDivaSyncHealth:
    return await IntegrationRepository().jobdiva_sync_health(
        stale_after_minutes=stale_after_minutes
    )
