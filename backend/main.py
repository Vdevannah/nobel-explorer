from fastapi import FastAPI

from backend.routes.health import router as health_router


app = FastAPI(
    title="Nobel Explorer API",
    description="Backend API for the Nobel Explorer educational application",
    version="0.1.0",
)


app.include_router(health_router)


@app.get("/")
def read_root():
    return {"message": "Nobel Explorer API is running"}