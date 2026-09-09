from sqlalchemy.orm import Session

from backend.repositories import analytics_repository
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
from backend.services.exceptions import ServiceValidationError


AGE_GROUP_ORDER = ["<30", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"]
ERA_ORDER = ["1901-1950", "1951-1970", "1971-1990", "1991-2010", "2011-present"]


def _validate_year_range(
    start_year: int | None,
    end_year: int | None
) -> None:
    """Shared start_year/end_year validation for the small, consistent
    Phase 10D filter set. Both bounds are individually validated for
    range by the route's Query(ge=..., le=...) constraints (a 422); this
    only checks the cross-field ordering constraint a single Query
    parameter can't express on its own.
    """
    if (
        start_year is not None
        and end_year is not None
        and start_year > end_year
    ):
        raise ServiceValidationError(
            "start_year must be less than or equal to end_year"
        )


def get_summary(
    db: Session,
    category: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None
) -> AnalyticsSummaryResponse:
    _validate_year_range(start_year, end_year)

    gender_counts = dict(
        analytics_repository.get_overall_gender_counts(
            db, category, start_year, end_year
        )
    )
    women_laureates = gender_counts.get("female", 0)
    total_gendered = sum(gender_counts.values())
    women_percentage = (
        round(women_laureates / total_gendered * 100, 1)
        if total_gendered else 0.0
    )

    return AnalyticsSummaryResponse(
        total_laureates=analytics_repository.count_total_laureates(
            db, category, start_year, end_year
        ),
        total_prizes=analytics_repository.count_total_prizes(
            db, category, start_year, end_year
        ),
        total_countries=analytics_repository.count_distinct_birth_countries(
            db, category, start_year, end_year
        ),
        women_laureates=women_laureates,
        women_percentage=women_percentage
    )


def get_top_countries(
    db: Session,
    limit: int = 5,
    category: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None
) -> list[CountryCountResponse]:
    _validate_year_range(start_year, end_year)
    results = analytics_repository.get_top_birth_countries(
        db, limit, category, start_year, end_year
    )
    return [
        CountryCountResponse(country=country, laureate_count=laureate_count)
        for country, laureate_count in results
    ]


def get_prize_counts_by_decade(
    db: Session,
    category: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None
) -> list[PrizeDecadeCountResponse]:
    _validate_year_range(start_year, end_year)
    results = analytics_repository.get_prize_counts_by_decade(
        db, category, start_year, end_year
    )
    return [
        PrizeDecadeCountResponse(decade=decade, prize_count=prize_count)
        for decade, prize_count in results
    ]


def get_age_distribution(
    db: Session,
    category: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None
) -> list[AgeDistributionResponse]:
    # `results` holds one age-at-award OBSERVATION count per bucket, not
    # a distinct-laureate count: a repeat winner with a known birth date
    # contributes one observation per award, so the same person can
    # appear in more than one bucket if their awards came at different
    # ages. `laureate_count` is kept as the field name for frontend
    # backward compatibility, but see get_age_distribution() in
    # analytics_repository.py for the exact counting method.
    _validate_year_range(start_year, end_year)
    results = dict(
        analytics_repository.get_age_distribution(
            db, category, start_year, end_year
        )
    )
    total = sum(results.values())

    return [
        AgeDistributionResponse(
            age_group=age_group,
            laureate_count=results.get(age_group, 0),
            percentage=(
                round(results.get(age_group, 0) / total * 100, 1)
                if total else 0.0
            )
        )
        for age_group in AGE_GROUP_ORDER
    ]


def get_women_percentage_by_era(
    db: Session,
    category: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None
) -> list[WomenEraResponse]:
    # `totals[era]` is the denominator: distinct person laureates with a
    # recorded gender who were associated with an award in that era.
    # Organizations and unknown-gender records never enter this sum (the
    # repository excludes them before grouping), so they can never be
    # implicitly counted as male or female.
    _validate_year_range(start_year, end_year)
    rows = analytics_repository.get_gender_counts_by_era(
        db, category, start_year, end_year
    )

    totals: dict[str, int] = {}
    female_totals: dict[str, int] = {}

    for era, gender, laureate_count in rows:
        totals[era] = totals.get(era, 0) + laureate_count
        if gender == "female":
            female_totals[era] = female_totals.get(era, 0) + laureate_count

    return [
        WomenEraResponse(
            era=era,
            percentage=round(
                female_totals.get(era, 0) / totals[era] * 100, 1
            ),
            women_count=female_totals.get(era, 0),
            known_gender_count=totals[era]
        )
        for era in ERA_ORDER
        if era in totals
    ]


def get_category_counts(
    db: Session,
    start_year: int | None = None,
    end_year: int | None = None
) -> list[CategoryCountResponse]:
    _validate_year_range(start_year, end_year)
    results = analytics_repository.get_laureate_counts_by_category(
        db, start_year, end_year
    )
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


def get_decade_counts(
    db: Session,
    category: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None
) -> list[DecadeCountResponse]:
    _validate_year_range(start_year, end_year)
    results = analytics_repository.get_laureate_counts_by_decade(
        db, category, start_year, end_year
    )
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


def get_categories_by_decade(
    db: Session,
    category: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None
) -> list[CategoryDecadeCountResponse]:
    _validate_year_range(start_year, end_year)
    results = analytics_repository.get_categories_by_decade(
        db, category, start_year, end_year
    )
    return [
        CategoryDecadeCountResponse(
            decade=decade,
            category=category_name,
            laureate_count=laureate_count
        )
        for decade, category_name, laureate_count in results
    ]
