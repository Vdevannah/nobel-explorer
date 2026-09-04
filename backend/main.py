from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.routes.analytics import router as analytics_router
from backend.routes.categories import router as categories_router
from backend.routes.health import router as health_router
from backend.routes.institutions import router as institutions_router
from backend.routes.laureates import router as laureates_router
from backend.routes.prizes import router as prizes_router
from backend.services.exceptions import ResourceNotFoundError


app = FastAPI(
    title="Nobel Explorer API",
    description=(
        "Explore Nobel Prize facts, laureates, prizes, award-time "
        "institutions, and analytics-ready educational data."
    ),
    version="1.0.0",
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


app.include_router(health_router)
app.include_router(analytics_router)
app.include_router(categories_router)
app.include_router(institutions_router)
app.include_router(laureates_router)
app.include_router(prizes_router)


@app.get("/")
def read_root():
    return {"message": "Nobel Explorer API is running"}
