from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.database.connection import get_db


router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "healthy"}


@router.get("/health/db")
def database_health(db: Session = Depends(get_db)):
    database_name = db.execute(
        text("SELECT DATABASE();")
    ).scalar()

    return {
        "status": "healthy",
        "database": database_name,
    }

