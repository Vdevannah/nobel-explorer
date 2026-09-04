from sqlalchemy.orm import Session

from backend.repositories import analytics_repository
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


def get_summary(db: Session) -> AnalyticsSummaryResponse:
    return AnalyticsSummaryResponse(
        total_laureates=analytics_repository.count_total_laureates(db),
        total_prizes=analytics_repository.count_total_prizes(db)
    )


def get_category_counts(db: Session) -> list[CategoryCountResponse]:
    results = analytics_repository.get_laureate_counts_by_category(db)
    return [
        CategoryCountResponse(
            category=category,
            laureate_count=laureate_count
        )
        for category, laureate_count in results
    ]


def get_country_counts(
    db: Session,
    category_name: str
) -> list[CountryCountResponse]:
    results = analytics_repository.get_laureate_counts_by_country_and_category(
        db,
        category_name
    )
    return [
        CountryCountResponse(
            country=country,
            laureate_count=laureate_count
        )
        for country, laureate_count in results
    ]


def get_us_state_counts(
    db: Session,
    category_name: str
) -> list[StateCountResponse]:
    results = analytics_repository.get_us_birth_state_counts_by_category(
        db,
        category_name
    )
    return [
        StateCountResponse(
            state=state,
            laureate_count=laureate_count
        )
        for state, laureate_count in results
    ]


def get_institution_counts(
    db: Session,
    category_name: str,
    country: str
) -> list[InstitutionCountResponse]:
    results = analytics_repository.get_institution_counts_by_category(
        db,
        category_name,
        country
    )
    return [
        InstitutionCountResponse(
            institution=institution,
            laureate_count=laureate_count
        )
        for institution, laureate_count in results
    ]


def get_gender_counts(
    db: Session,
    category_name: str
) -> list[GenderCountResponse]:
    results = analytics_repository.get_gender_counts_by_category(
        db,
        category_name
    )
    return [
        GenderCountResponse(
            gender=gender,
            laureate_count=laureate_count
        )
        for gender, laureate_count in results
    ]


def get_decade_counts(db: Session) -> list[DecadeCountResponse]:
    results = analytics_repository.get_laureate_counts_by_decade(db)
    return [
        DecadeCountResponse(
            decade=decade,
            laureate_count=laureate_count
        )
        for decade, laureate_count in results
    ]


def get_average_age(
    db: Session,
    category_name: str
) -> AverageAgeResponse:
    average_age = analytics_repository.get_average_age_at_award_by_category(
        db,
        category_name
    )
    return AverageAgeResponse(
        category=category_name,
        average_age=average_age
    )
