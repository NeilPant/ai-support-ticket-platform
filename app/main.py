from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import get_settings
from app.core.database import check_database, init_db
from app.core.logging import configure_logging
from app.models.ticket import ReadinessResponse

configure_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    description=(
        "AI-heavy support ticket platform with FastAPI, LangGraph orchestration, "
        "local RAG, persisted workflow runs, and production-ready API patterns."
    ),
    version="2.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": str(exc), "request_id": request_id},
    )


app.include_router(router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


@app.get("/readiness", response_model=ReadinessResponse, tags=["health"])
def readiness_check() -> ReadinessResponse:
    # Knowledge indexing is intentionally lazy; readiness reports whether the DB is available.
    return ReadinessResponse(
        status="ready" if check_database() else "not_ready",
        database=check_database(),
        knowledge_index=True,
        llm_mode="openai" if settings.use_llm and settings.openai_api_key else "deterministic_fallback",
    )
