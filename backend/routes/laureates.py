from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.schemas.laureate import (
    LaureateDetailResponse,
    PaginatedLaureatesResponse,
)
from backend.schemas.contribution import ContributionResponse, ContributionType
from backend.services import contribution_service
from backend.services import laureate_service


router = APIRouter(
    prefix="/laureates",
    tags=["Laureates"]
)


@router.get(
    "/{laureate_id}/contributions",
    response_model=list[ContributionResponse],
    summary="List educational contributions for a laureate",
    responses={404: {"description": "Laureate not found"}},
)
def list_laureate_contributions(
    laureate_id: int = Path(
        description="Nobel Explorer internal laureate database ID"
    ),
    contribution_type: ContributionType | None = Query(
        default=None,
        description="Optional Nobel-linked or beyond-Nobel filter",
    ),
    db: Session = Depends(get_db),
):
    return contribution_service.list_laureate_contributions(
        db, laureate_id, contribution_type
    )


@router.get(
    "",
    response_model=PaginatedLaureatesResponse,
    summary="List and search laureates"
)
def list_laureates(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of results returned"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of matching results to skip"
    ),
    category: str | None = Query(
        default=None,
        description="Nobel Prize category filter"
    ),
    year: int | None = Query(
        default=None,
        description="Nobel Prize award year filter"
    ),
    country: str | None = Query(
        default=None,
        description="Laureate birth country filter"
    ),
    gender: str | None = Query(
        default=None,
        description="Laureate gender filter"
    ),
    search: str | None = Query(
        default=None,
        description="Case-insensitive laureate name substring"
    ),
    db: Session = Depends(get_db)
):
    return laureate_service.list_laureates(
        db,
        limit,
        offset,
        category,
        year,
        country,
        gender,
        search
    )


@router.get(
    "/{laureate_id}",
    response_model=LaureateDetailResponse,
    summary="Get laureate details",
    responses={404: {"description": "Laureate not found"}}
)
def get_laureate(
    laureate_id: int = Path(
        description=(
            "Nobel Explorer internal laureate database ID; "
            "not the Nobel API ID"
        )
    ),
    db: Session = Depends(get_db)
):
    return laureate_service.get_laureate(db, laureate_id)
