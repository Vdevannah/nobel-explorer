from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.schemas.institution import (
    InstitutionResponse,
    PaginatedInstitutionAwardsResponse,
    PaginatedInstitutionsResponse,
)
from backend.services import institution_service


router = APIRouter(
    prefix="/institutions",
    tags=["Institutions"]
)


@router.get(
    "",
    response_model=PaginatedInstitutionsResponse,
    summary="List award-time institutions"
)
def list_institutions(
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
    db: Session = Depends(get_db)
):
    return institution_service.list_institutions(db, limit, offset)


@router.get(
    "/{institution_id}",
    response_model=InstitutionResponse,
    summary="Get institution details",
    responses={404: {"description": "Institution not found"}}
)
def get_institution(
    institution_id: int = Path(
        description="Nobel Explorer internal institution database ID"
    ),
    db: Session = Depends(get_db)
):
    return institution_service.get_institution(db, institution_id)


@router.get(
    "/{institution_id}/awards",
    response_model=PaginatedInstitutionAwardsResponse,
    summary="List Nobel affiliations for an institution",
    description=(
        "Lists Nobel award relationships associated with this "
        "award-time institution."
    ),
    responses={404: {"description": "Institution not found"}}
)
def list_institution_awards(
    institution_id: int = Path(
        description="Nobel Explorer internal institution database ID"
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of affiliation results returned"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of affiliation results to skip"
    ),
    db: Session = Depends(get_db)
):
    return institution_service.list_institution_awards(
        db,
        institution_id,
        limit,
        offset
    )
