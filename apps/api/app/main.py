from fastapi import FastAPI

app = FastAPI(
    title="Medlivo AI Platform API",
    version="0.1.0",
)

@app.get("/health")
async def health() -> dict[str, str | bool]:
    return {
        "ok": True,
        "service": "medlivo-ai-api",
        "phase": "foundation",
    }

@app.get("/api/v1/platform")
async def platform() -> dict[str, object]:
    return {
        "product": "Medlivo AI Platform",
        "phase": 1,
        "surfaces": ["recruit.medlivo.com"],
        "status": "foundation",
    }
