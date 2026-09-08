import os

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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


app = FastAPI(
    title="Nobel Explorer API",
    description=(
        "Explore Nobel Prize facts, laureates, prizes, award-time "
        "institutions, and analytics-ready educational data."
    ),
    version="1.0.0",
)

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


@app.get("/")
def read_root():
    return {"message": "Nobel Explorer API is running"}
