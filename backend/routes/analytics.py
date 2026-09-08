from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.schemas.analytics import (
    AgeDistributionResponse,
    AnalyticsSummaryResponse,
    AverageAgeResponse,
    CategoryCountResponse,
    CategoryDecadeCountResponse,
    CountryCountResponse,
    DecadeCountResponse,
    GenderCountResponse,
    InstitutionCountResponse,
    PrizeDecadeCountResponse,
    StateCountResponse,
    WomenEraResponse,
)
from backend.services import analytics_service


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)


# Phase 10D: the small, consistent filter set (category/start_year/
# end_year) shared by the six dashboard endpoints below. Both years are
# independently optional (one-sided ranges are supported); the bounds
# here reject obviously-invalid years with FastAPI's own 422, while the
# start_year <= end_year ordering check (which spans two parameters) is
# done once in analytics_service._validate_year_range and returns 400.
MIN_NOBEL_YEAR = 1901
MAX_NOBEL_YEAR = 2100

CATEGORY_FILTER_DESCRIPTION = "Optional Nobel Prize category filter"
START_YEAR_FILTER_DESCRIPTION = "Optional inclusive start year (Nobel-era year, e.g. 1901+)"
END_YEAR_FILTER_DESCRIPTION = "Optional inclusive end year (Nobel-era year, e.g. 1901+)"


@router.get(
    "/summary",
    response_model=AnalyticsSummaryResponse,
    summary="Get Nobel Explorer totals",
    description=(
        "Returns counts of all laureate rows (people and organizations), "
        "Prize rows, distinct recorded birth countries among people, women "
        "among people with known gender, and that count as a percentage of "
        "people with known gender."
    ),
)
def get_summary(db: Session = Depends(get_db)):
    return analytics_service.get_summary(db)


@router.get(
    "/laureates-by-category",
    response_model=list[CategoryCountResponse],
    summary="Count distinct laureates by category",
    description=(
        "Counts each laureate once within a Nobel Prize category. A "
        "laureate recognized in multiple categories appears once in each. "
        "Optional start_year/end_year narrow this to awards within that "
        "range (no category filter here -- category is already the "
        "grouping key)."
    ),
)
def get_laureates_by_category(
    start_year: int | None = Query(
        default=None,
        ge=MIN_NOBEL_YEAR,
        le=MAX_NOBEL_YEAR,
        description=START_YEAR_FILTER_DESCRIPTION
    ),
    end_year: int | None = Query(
        default=None,
        ge=MIN_NOBEL_YEAR,
        le=MAX_NOBEL_YEAR,
        description=END_YEAR_FILTER_DESCRIPTION
    ),
    db: Session = Depends(get_db)
):
    return analytics_service.get_category_counts(db, start_year, end_year)


@router.get(
    "/birth-countries",
    response_model=list[CountryCountResponse],
    summary="Count laureates by birth country",
    description=(
        "Counts person laureates (organizations excluded) by their "
        "recorded birth_country for a Nobel Prize category. This is "
        "birthplace-based, not nationality or citizenship."
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
        "Counts USA-born person laureates (organizations excluded) by "
        "full stored birth-state name for a Nobel Prize category."
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
    summary="Count people by gender within a category",
    description=(
        "Counts distinct person laureates with a recorded gender. "
        "Organizations and records without gender are excluded."
    ),
)
def get_gender(
    category: str = Query(
        description="Nobel Prize category used for gender counts"
    ),
    db: Session = Depends(get_db)
):
    return analytics_service.get_gender_counts(db, category)


@router.get(
    "/top-countries",
    response_model=list[CountryCountResponse],
    summary="Get top birth countries by laureate count",
    description=(
        "Ranks recorded birth countries for person laureates (organizations "
        "excluded). Birth country is birthplace data, not nationality or "
        "citizenship. Optionally narrowed by category and/or start_year/"
        "end_year."
    ),
)
def get_top_countries(
    limit: int = Query(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of countries to return"
    ),
    category: str | None = Query(
        default=None,
        description=CATEGORY_FILTER_DESCRIPTION
    ),
    start_year: int | None = Query(
        default=None,
        ge=MIN_NOBEL_YEAR,
        le=MAX_NOBEL_YEAR,
        description=START_YEAR_FILTER_DESCRIPTION
    ),
    end_year: int | None = Query(
        default=None,
        ge=MIN_NOBEL_YEAR,
        le=MAX_NOBEL_YEAR,
        description=END_YEAR_FILTER_DESCRIPTION
    ),
    db: Session = Depends(get_db)
):
    return analytics_service.get_top_countries(
        db, limit, category, start_year, end_year
    )


@router.get(
    "/prizes-by-decade",
    response_model=list[PrizeDecadeCountResponse],
    summary="Count Prize rows by award decade",
    description=(
        "Counts distinct Prize records grouped into 10-year decades "
        "derived from each Prize's award year (e.g. 1987 falls in 1980). "
        "Optionally narrowed by category and/or start_year/end_year."
    ),
)
def get_prizes_by_decade(
    category: str | None = Query(
        default=None,
        description=CATEGORY_FILTER_DESCRIPTION
    ),
    start_year: int | None = Query(
        default=None,
        ge=MIN_NOBEL_YEAR,
        le=MAX_NOBEL_YEAR,
        description=START_YEAR_FILTER_DESCRIPTION
    ),
    end_year: int | None = Query(
        default=None,
        ge=MIN_NOBEL_YEAR,
        le=MAX_NOBEL_YEAR,
        description=END_YEAR_FILTER_DESCRIPTION
    ),
    db: Session = Depends(get_db)
):
    return analytics_service.get_prize_counts_by_decade(
        db, category, start_year, end_year
    )


@router.get(
    "/age-distribution",
    response_model=list[AgeDistributionResponse],
    summary="Get laureate age-at-award distribution",
    description=(
        "Buckets age-at-award OBSERVATIONS (one per award with a known "
        "birth date) by approximate age (Prize year minus birth year), "
        "across every category. A repeat winner contributes one "
        "observation per award, so the same person may appear in more "
        "than one bucket if their awards came at different ages. "
        "Organizations have no birth date and are excluded. Optionally "
        "narrowed by category and/or start_year/end_year."
    )
)
def get_age_distribution(
    category: str | None = Query(
        default=None,
        description=CATEGORY_FILTER_DESCRIPTION
    ),
    start_year: int | None = Query(
        default=None,
        ge=MIN_NOBEL_YEAR,
        le=MAX_NOBEL_YEAR,
        description=START_YEAR_FILTER_DESCRIPTION
    ),
    end_year: int | None = Query(
        default=None,
        ge=MIN_NOBEL_YEAR,
        le=MAX_NOBEL_YEAR,
        description=END_YEAR_FILTER_DESCRIPTION
    ),
    db: Session = Depends(get_db)
):
    return analytics_service.get_age_distribution(
        db, category, start_year, end_year
    )


@router.get(
    "/women-by-era",
    response_model=list[WomenEraResponse],
    summary="Get women as a percentage of known-gender people by era",
    description=(
        "For each award-year era, divides distinct women laureates by "
        "distinct person laureates with known gender who were associated "
        "with an award in that era, and returns both raw counts "
        "(women_count, known_gender_count) alongside the percentage for "
        "transparency. This is NOT a percentage of prizes awarded to "
        "women. Organizations and unknown-gender records are excluded "
        "entirely -- never counted as male or female. Optionally narrowed "
        "by category and/or start_year/end_year."
    ),
)
def get_women_by_era(
    category: str | None = Query(
        default=None,
        description=CATEGORY_FILTER_DESCRIPTION
    ),
    start_year: int | None = Query(
        default=None,
        ge=MIN_NOBEL_YEAR,
        le=MAX_NOBEL_YEAR,
        description=START_YEAR_FILTER_DESCRIPTION
    ),
    end_year: int | None = Query(
        default=None,
        ge=MIN_NOBEL_YEAR,
        le=MAX_NOBEL_YEAR,
        description=END_YEAR_FILTER_DESCRIPTION
    ),
    db: Session = Depends(get_db)
):
    return analytics_service.get_women_percentage_by_era(
        db, category, start_year, end_year
    )


@router.get(
    "/decades",
    response_model=list[DecadeCountResponse],
    summary="Count distinct laureates by award decade",
    description=(
        "Counts each laureate once within each decade containing an "
        "associated Prize. A repeat laureate may appear in multiple "
        "decades. Optionally narrowed by category and/or start_year/"
        "end_year."
    ),
)
def get_decades(
    category: str | None = Query(
        default=None,
        description=CATEGORY_FILTER_DESCRIPTION
    ),
    start_year: int | None = Query(
        default=None,
        ge=MIN_NOBEL_YEAR,
        le=MAX_NOBEL_YEAR,
        description=START_YEAR_FILTER_DESCRIPTION
    ),
    end_year: int | None = Query(
        default=None,
        ge=MIN_NOBEL_YEAR,
        le=MAX_NOBEL_YEAR,
        description=END_YEAR_FILTER_DESCRIPTION
    ),
    db: Session = Depends(get_db)
):
    return analytics_service.get_decade_counts(
        db, category, start_year, end_year
    )


@router.get(
    "/categories-by-decade",
    response_model=list[CategoryDecadeCountResponse],
    summary="Get distinct laureates by category, per decade",
    description=(
        "Phase 10E trend endpoint: counts DISTINCT laureates within each "
        "category, for each 10-year decade derived from the Prize award "
        "year, so recognition across fields can be compared over time. "
        "Optionally narrowed by category and/or start_year/end_year."
    ),
)
def get_categories_by_decade(
    category: str | None = Query(
        default=None,
        description=CATEGORY_FILTER_DESCRIPTION
    ),
    start_year: int | None = Query(
        default=None,
        ge=MIN_NOBEL_YEAR,
        le=MAX_NOBEL_YEAR,
        description=START_YEAR_FILTER_DESCRIPTION
    ),
    end_year: int | None = Query(
        default=None,
        ge=MIN_NOBEL_YEAR,
        le=MAX_NOBEL_YEAR,
        description=END_YEAR_FILTER_DESCRIPTION
    ),
    db: Session = Depends(get_db)
):
    return analytics_service.get_categories_by_decade(
        db, category, start_year, end_year
    )


@router.get(
    "/average-age",
    response_model=AverageAgeResponse,
    summary="Get approximate average age at award",
    description=(
        "Calculates approximate age at award for a category using the "
        "Prize award year and known birth dates of person laureates "
        "(organizations excluded). Averages over age-at-award "
        "observations, one per award, so a repeat winner in this "
        "category contributes one observation per award rather than "
        "being collapsed to a single age."
    )
)
def get_average_age(
    category: str = Query(
        description="Nobel Prize category used for average-age calculation"
    ),
    db: Session = Depends(get_db)
):
    return analytics_service.get_average_age(db, category)
