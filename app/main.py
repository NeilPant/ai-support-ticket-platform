from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=(
        "REST APIs for AI-assisted customer support ticket triage, "
        "LangGraph orchestration, escalation routing, and analytics."
    ),
    version="1.0.0",
)

app.include_router(router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
