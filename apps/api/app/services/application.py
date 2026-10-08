from app.db.database import database_configured
from app.repositories.application import CareerApplicationRepository
from app.schemas.application import CareerApplicationInput, CareerApplicationReceipt


_repository = CareerApplicationRepository()


async def submit_career_application(value: CareerApplicationInput) -> CareerApplicationReceipt:
    if not database_configured():
        raise RuntimeError("Career database is not configured")
    return await _repository.create(value)
