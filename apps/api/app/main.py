from fastapi import FastAPI

from app.routes.recruiting import router as recruiting_router

app = FastAPI(
    title="Medlivo AI Platform API",
    version="0.1.0",
)

app.include_router(recruiting_router)


@app.get("/health")
async def health() -> dict[str, str | bool]:
    return {
        "ok": True,
        "service": "medlivo-ai-api",
        "phase": "vertical-slice-1",
    }


@app.get("/api/v1/platform")
async def platform() -> dict[str, object]:
    return {
        "product": "Medlivo AI Platform",
        "phase": 1,
        "surfaces": ["recruit.medlivo.com"],
        "status": "vertical-slice-1",
    }
