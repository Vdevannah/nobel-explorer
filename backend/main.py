import logging
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.ai.guard import BodySizeLimitMiddleware, GuardConfig
from backend.routes.ai import router as ai_router
from backend.routes.analytics import router as analytics_router
from backend.routes.categories import router as categories_router
from backend.routes.contributions import router as contributions_router
from backend.routes.health import router as health_router
from backend.routes.institutions import router as institutions_router
from backend.routes.laureates import router as laureates_router
from backend.routes.prizes import router as prizes_router
from backend.routes.quiz_questions import router as quiz_questions_router
from backend.services.exceptions import ResourceNotFoundError, ServiceValidationError


DEFAULT_FRONTEND_ORIGINS = (
    "http://localhost:5173,http://127.0.0.1:5173"
)
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        DEFAULT_FRONTEND_ORIGINS
    ).split(",")
    if origin.strip()
]


logger = logging.getLogger(__name__)


def _warm_up_ai() -> None:
    """Load the embedding model and open the index so the first question does not
    pay the cold start. Runs in a background thread; failures are only logged."""
    try:
        from backend.ai.retrieval import get_default_store

        store = get_default_store()
        store.embedder.embed_query("Nobel Prize")
        logger.info("AI warm-up complete: %s indexed chunks", store.count())
    except Exception as exc:  # noqa: BLE001 - never block or crash the API
        logger.warning("AI warm-up failed: %s", type(exc).__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Only when the assistant is enabled; disabled deployments never load the model.
    from backend.ai.agent.config import AgentConfigError, load_agent_config

    try:
        enabled = load_agent_config().availability()[0]
    except AgentConfigError:
        enabled = False
    if enabled and os.getenv("AI_WARMUP", "true").strip().lower() not in {"0", "false", "no", "off"}:
        threading.Thread(target=_warm_up_ai, name="ai-warm-up", daemon=True).start()
    yield


try:
    MAX_AI_BODY_BYTES = GuardConfig.from_env().max_body_bytes
except ValueError:
    MAX_AI_BODY_BYTES = GuardConfig.max_body_bytes


app = FastAPI(
    lifespan=lifespan,
    title="Nobel Explorer API",
    description=(
        "Explore Nobel Prize facts, laureates, prizes, award-time "
        "institutions, and analytics-ready educational data."
    ),
    version="1.0.0",
)

# Added before CORS so that CORS stays the outermost layer.
app.add_middleware(BodySizeLimitMiddleware, max_bytes=MAX_AI_BODY_BYTES, prefix="/ai/")
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Accept", "Content-Type"],
)


@app.exception_handler(ResourceNotFoundError)
async def resource_not_found_handler(
    request: Request,
    error: ResourceNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(error)}
    )


@app.exception_handler(ServiceValidationError)
async def service_validation_handler(
    request: Request,
    error: ServiceValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(error)},
    )


app.include_router(health_router)
app.include_router(analytics_router)
app.include_router(categories_router)
app.include_router(contributions_router)
app.include_router(institutions_router)
app.include_router(laureates_router)
app.include_router(prizes_router)
app.include_router(quiz_questions_router)
app.include_router(ai_router)


@app.get("/")
def read_root():
    return {"message": "Nobel Explorer API is running"}
