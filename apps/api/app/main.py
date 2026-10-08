from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routes.recruiting import router as recruiting_router
from app.routes.career import router as career_router
from app.routes.integration import router as integration_router
from app.db.database import open_database, close_database

@asynccontextmanager
async def lifespan(app: FastAPI):
    await open_database()
    try:
        yield
    finally:
        await close_database()


app = FastAPI(
    title="Medlivo AI Platform API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(recruiting_router)
app.include_router(career_router)
app.include_router(integration_router)


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
