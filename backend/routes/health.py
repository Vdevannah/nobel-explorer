from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.database.connection import get_db


router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Check application health",
    description="Confirms that the Nobel Explorer API is running."
)
def health_check():
    return {"status": "healthy"}


@router.get(
    "/health/db",
    summary="Check database connectivity",
    description="Confirms that the API can connect to its MySQL database."
)
def database_health(db: Session = Depends(get_db)):
    database_name = db.execute(
        text("SELECT DATABASE();")
    ).scalar()

    return {
        "status": "healthy",
        "database": database_name,
    }
