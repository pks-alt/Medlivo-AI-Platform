from fastapi import APIRouter, HTTPException, Response

from app.schemas.application import CareerApplicationInput, CareerApplicationReceipt
from app.services.application import submit_career_application


router = APIRouter(prefix="/api/v1/careers", tags=["careers"])


@router.post("/applications", response_model=CareerApplicationReceipt, status_code=201)
async def apply(value: CareerApplicationInput, response: Response) -> CareerApplicationReceipt:
    try:
        result = await submit_career_application(value)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Applications are temporarily unavailable") from exc
    response.headers["Cache-Control"] = "no-store"
    return result
