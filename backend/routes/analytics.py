from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.schemas.analytics import (
    AnalyticsSummaryResponse,
    AverageAgeResponse,
    CategoryCountResponse,
    CountryCountResponse,
    DecadeCountResponse,
    GenderCountResponse,
    InstitutionCountResponse,
    StateCountResponse,
)
from backend.services import analytics_service


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)


@router.get(
    "/summary",
    response_model=AnalyticsSummaryResponse,
    summary="Get Nobel Explorer totals"
)
def get_summary(db: Session = Depends(get_db)):
    return analytics_service.get_summary(db)


@router.get(
    "/laureates-by-category",
    response_model=list[CategoryCountResponse],
    summary="Count laureates by category"
)
def get_laureates_by_category(db: Session = Depends(get_db)):
    return analytics_service.get_category_counts(db)


@router.get(
    "/birth-countries",
    response_model=list[CountryCountResponse],
    summary="Count laureates by birth country",
    description=(
        "Counts individual Laureates by their recorded birth_country "
        "for a Nobel Prize category. This is birthplace-based."
    )
)
def get_birth_countries(
    category: str = Query(
        description="Nobel Prize category used for birthplace counts"
    ),
    db: Session = Depends(get_db)
):
    return analytics_service.get_country_counts(db, category)


@router.get(
    "/us-birth-states",
    response_model=list[StateCountResponse],
    summary="Count laureates by U.S. birth state",
    description=(
        "Counts USA-born individual Laureates by full stored birth-state "
        "name for a Nobel Prize category."
    )
)
def get_us_birth_states(
    category: str = Query(
        description="Nobel Prize category used for U.S. birthplace counts"
    ),
    db: Session = Depends(get_db)
):
    return analytics_service.get_us_state_counts(db, category)


@router.get(
    "/institutions",
    response_model=list[InstitutionCountResponse],
    summary="Count laureates by award-time institution",
    description=(
        "Counts Nobel-affiliated Laureates by award-time institution for "
        "a category and institution country. This is not birthplace data."
    )
)
def get_institutions(
    category: str = Query(
        description="Nobel Prize category used for affiliation counts"
    ),
    country: str = Query(
        description="Award-time institution country, such as USA"
    ),
    db: Session = Depends(get_db)
):
    return analytics_service.get_institution_counts(
        db,
        category,
        country
    )


@router.get(
    "/gender",
    response_model=list[GenderCountResponse],
    summary="Count laureates by gender"
)
def get_gender(
    category: str = Query(
        description="Nobel Prize category used for gender counts"
    ),
    db: Session = Depends(get_db)
):
    return analytics_service.get_gender_counts(db, category)


@router.get(
    "/decades",
    response_model=list[DecadeCountResponse],
    summary="Count laureates by award decade"
)
def get_decades(db: Session = Depends(get_db)):
    return analytics_service.get_decade_counts(db)


@router.get(
    "/average-age",
    response_model=AverageAgeResponse,
    summary="Get approximate average age at award",
    description=(
        "Calculates approximate age at award for a category using the "
        "Prize award year and known Laureate birth dates."
    )
)
def get_average_age(
    category: str = Query(
        description="Nobel Prize category used for average-age calculation"
    ),
    db: Session = Depends(get_db)
):
    return analytics_service.get_average_age(db, category)
