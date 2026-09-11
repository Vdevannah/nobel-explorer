from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.schemas.prize import (
    PaginatedPrizesResponse,
    PrizeDetailResponse,
)
from backend.services import prize_service


router = APIRouter(
    prefix="/prizes",
    tags=["Prizes"]
)


@router.get(
    "",
    response_model=PaginatedPrizesResponse,
    summary="List Nobel Prizes"
)
def list_prizes(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of results returned"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of results to skip"
    ),
    category: str | None = Query(
        default=None,
        description="Nobel Prize category filter"
    ),
    year: int | None = Query(
        default=None,
        ge=1901,
        le=2025,
        description="Nobel Prize award year filter"
    ),
    db: Session = Depends(get_db)
):
    return prize_service.list_prizes(
        db, limit, offset, category, year
    )


@router.get(
    "/{prize_id}",
    response_model=PrizeDetailResponse,
    summary="Get Nobel Prize details",
    responses={404: {"description": "Prize not found"}}
)
def get_prize(
    prize_id: int = Path(
        description="Nobel Explorer internal prize database ID"
    ),
    db: Session = Depends(get_db)
):
    return prize_service.get_prize(db, prize_id)
