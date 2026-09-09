from sqlalchemy import case, select, func
from sqlalchemy.orm import Session

from backend.models.category import Category
from backend.models.prize import Prize
from backend.models.laureate import Laureate
from backend.models.laureate_prize import LaureatePrize
from backend.models.institution import Institution
from backend.models.award_affiliation import AwardAffiliation


def _year_range_conditions(
    start_year: int | None,
    end_year: int | None
) -> list:
    """Build optional Prize.year >= / <= conditions for the small,
    consistent category/start_year/end_year filter set (Phase 10D).
    Both bounds are optional and independent (one-sided ranges are
    supported); returns an empty list when neither is supplied, so
    passing it into a `.where(*conditions)` call is always safe and
    changes nothing for existing unfiltered callers.
    """
    conditions = []
    if start_year is not None:
        conditions.append(Prize.year >= start_year)
    if end_year is not None:
        conditions.append(Prize.year <= end_year)
    return conditions


def count_total_laureates(
    db: Session,
    category: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None
) -> int:
    # Joining through LaureatePrize/Prize (rather than a plain count of
    # all Laureate rows) is a no-op when no filters are supplied: every
    # laureate is tied to at least one Prize, so the distinct-through-join
    # count matches the unfiltered total exactly (verified against the
    # 1,018-laureate baseline). This lets the same query serve both the
    # unfiltered summary and the Phase 10D category/start_year/end_year
    # filtered summary.
    conditions = _year_range_conditions(start_year, end_year)
    if category is not None:
        conditions.append(Category.name == category)

    statement = (
        select(
            func.count(func.distinct(Laureate.laureate_id))
        )
        .join(
            LaureatePrize,
            LaureatePrize.laureate_id == Laureate.laureate_id
        )
        .join(
            Prize,
            Prize.prize_id == LaureatePrize.prize_id
        )
    )
    if category is not None:
        statement = statement.join(
            Category,
            Category.category_id == Prize.category_id
        )
    if conditions:
        statement = statement.where(*conditions)

    return db.scalar(statement) or 0


def count_total_prizes(
    db: Session,
    category: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None
) -> int:
    conditions = _year_range_conditions(start_year, end_year)
    if category is not None:
        conditions.append(Category.name == category)

    statement = select(
        func.count(func.distinct(Prize.prize_id))
    )
    if category is not None:
        statement = statement.join(
            Category,
            Category.category_id == Prize.category_id
        )
    if conditions:
        statement = statement.where(*conditions)

    return db.scalar(statement) or 0


def count_distinct_birth_countries(
    db: Session,
    category: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None
) -> int:
    conditions = [
        Laureate.birth_country.is_not(None),
        Laureate.laureate_type == "Person",
        *_year_range_conditions(start_year, end_year)
    ]
    if category is not None:
        conditions.append(Category.name == category)

    statement = (
        select(
            func.count(func.distinct(Laureate.birth_country))
        )
        .join(
            LaureatePrize,
            LaureatePrize.laureate_id == Laureate.laureate_id
        )
        .join(
            Prize,
            Prize.prize_id == LaureatePrize.prize_id
        )
    )
    if category is not None:
        statement = statement.join(
            Category,
            Category.category_id == Prize.category_id
        )
    statement = statement.where(*conditions)

    return db.scalar(statement) or 0


def get_overall_gender_counts(
    db: Session,
    category: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None
) -> list[tuple[str, int]]:
    conditions = [
        Laureate.laureate_type == "Person",
        Laureate.gender.is_not(None),
        *_year_range_conditions(start_year, end_year)
    ]
    if category is not None:
        conditions.append(Category.name == category)

    statement = (
        select(
            Laureate.gender,
            func.count(
                func.distinct(Laureate.laureate_id)
            ).label("laureate_count")
        )
        .join(
            LaureatePrize,
            LaureatePrize.laureate_id == Laureate.laureate_id
        )
        .join(
            Prize,
            Prize.prize_id == LaureatePrize.prize_id
        )
    )
    if category is not None:
        statement = statement.join(
            Category,
            Category.category_id == Prize.category_id
        )
    statement = statement.where(*conditions).group_by(Laureate.gender)

    return list(db.execute(statement).all())


def get_top_birth_countries(
    db: Session,
    limit: int = 5,
    category: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None
) -> list[tuple[str, int]]:

    conditions = [
        Laureate.birth_country.is_not(None),
        Laureate.laureate_type == "Person",
        *_year_range_conditions(start_year, end_year)
    ]
    if category is not None:
        conditions.append(Category.name == category)

    statement = (
        select(
            Laureate.birth_country,
            func.count(
                func.distinct(Laureate.laureate_id)
            ).label("laureate_count")
        )
        .join(
            LaureatePrize,
            LaureatePrize.laureate_id == Laureate.laureate_id
        )
        .join(
            Prize,
            Prize.prize_id == LaureatePrize.prize_id
        )
        .join(
            Category,
            Category.category_id == Prize.category_id
        )
        .where(*conditions)
        .group_by(Laureate.birth_country)
        .order_by(
            func.count(
                func.distinct(Laureate.laureate_id)
            ).desc()
        )
        .limit(limit)
    )

    return list(db.execute(statement).all())


def get_prize_counts_by_decade(
    db: Session,
    category: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None
) -> list[tuple[int, int]]:

    decade = (
        func.floor(Prize.year / 10) * 10
    ).label("decade")

    conditions = _year_range_conditions(start_year, end_year)

    statement = select(
        decade,
        func.count(
            func.distinct(Prize.prize_id)
        ).label("prize_count")
    )

    if category is not None:
        statement = statement.join(
            Category,
            Category.category_id == Prize.category_id
        )
        conditions.append(Category.name == category)

    if conditions:
        statement = statement.where(*conditions)

    statement = statement.group_by(decade).order_by(decade)

    return list(db.execute(statement).all())


def get_age_distribution(
    db: Session,
    category: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None
) -> list[tuple[str, int]]:
    """Bucket age-at-award OBSERVATIONS (one per LaureatePrize row with a
    known birth date), not distinct laureates. A repeat winner with a
    known birth date contributes one observation per award, and those
    observations may land in different age groups if the awards came at
    different ages -- this is intentional (Phase 10F methodology), not a
    double-count bug. Counting `LaureatePrize.laureate_prize_id` (the
    join's own primary key) rather than `Laureate.laureate_id` is what
    makes each award count as its own observation. The optional
    category/start_year/end_year filters (Phase 10D) narrow which
    observations are counted; they never change this counting method.
    """
    age_at_award = Prize.year - func.year(Laureate.birth_date)

    age_group = case(
        (age_at_award < 30, "<30"),
        (age_at_award < 40, "30-39"),
        (age_at_award < 50, "40-49"),
        (age_at_award < 60, "50-59"),
        (age_at_award < 70, "60-69"),
        (age_at_award < 80, "70-79"),
        else_="80+"
    ).label("age_group")

    conditions = [
        Laureate.laureate_type == "Person",
        Laureate.birth_date.is_not(None),
        *_year_range_conditions(start_year, end_year)
    ]
    if category is not None:
        conditions.append(Category.name == category)

    statement = (
        select(
            age_group,
            func.count(
                func.distinct(LaureatePrize.laureate_prize_id)
            ).label("observation_count")
        )
        .join(
            LaureatePrize,
            LaureatePrize.prize_id == Prize.prize_id
        )
        .join(
            Laureate,
            Laureate.laureate_id == LaureatePrize.laureate_id
        )
        .join(
            Category,
            Category.category_id == Prize.category_id
        )
        .where(*conditions)
        .group_by(age_group)
    )

    return list(db.execute(statement).all())


def get_gender_counts_by_era(
    db: Session,
    category: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None
) -> list[tuple[str, str, int]]:
    """Count DISTINCT person laureates with known gender per era, not
    award observations: a laureate who won twice within the same era is
    still one person in that era's denominator. Organizations and
    unknown-gender records are excluded entirely (never counted, and
    never treated as a gender). This is the locked women-by-era
    methodology from Phase 10C/10F and is unchanged from prior phases.
    The optional category/start_year/end_year filters (Phase 10D)
    narrow which awards are considered before era-bucketing; they never
    change the distinct-person counting method.
    """
    era = case(
        (Prize.year <= 1950, "1901-1950"),
        (Prize.year <= 1970, "1951-1970"),
        (Prize.year <= 1990, "1971-1990"),
        (Prize.year <= 2010, "1991-2010"),
        else_="2011-present"
    ).label("era")

    conditions = [
        Laureate.laureate_type == "Person",
        Laureate.gender.is_not(None),
        *_year_range_conditions(start_year, end_year)
    ]
    if category is not None:
        conditions.append(Category.name == category)

    statement = (
        select(
            era,
            Laureate.gender,
            func.count(
                func.distinct(Laureate.laureate_id)
            ).label("laureate_count")
        )
        .join(
            LaureatePrize,
            LaureatePrize.prize_id == Prize.prize_id
        )
        .join(
            Laureate,
            Laureate.laureate_id == LaureatePrize.laureate_id
        )
        .join(
            Category,
            Category.category_id == Prize.category_id
        )
        .where(*conditions)
        .group_by(era, Laureate.gender)
    )

    return list(db.execute(statement).all())


def get_laureate_counts_by_category(
    db: Session,
    start_year: int | None = None,
    end_year: int | None = None
) -> list[tuple[str, int]]:
    # No `category` filter here: category is already this query's
    # group-by key, so filtering by it would just collapse the result
    # to one row -- start_year/end_year (Phase 10D) narrow the awards
    # considered within each category instead.

    conditions = _year_range_conditions(start_year, end_year)

    statement = (
        select(
            Category.name,
            func.count(
                func.distinct(Laureate.laureate_id)
            ).label("laureate_count")
        )
        .join(
            Prize,
            Prize.category_id == Category.category_id
        )
        .join(
            LaureatePrize,
            LaureatePrize.prize_id == Prize.prize_id
        )
        .join(
            Laureate,
            Laureate.laureate_id == LaureatePrize.laureate_id
        )
    )

    if conditions:
        statement = statement.where(*conditions)

    statement = statement.group_by(Category.name).order_by(
        func.count(
            func.distinct(Laureate.laureate_id)
        ).desc()
    )

    return list(db.execute(statement).all())

def get_laureate_counts_by_country_and_category(
    db: Session,
    category_name: str
) -> list[tuple[str, int]]:

    statement = (
        select(
            Laureate.birth_country,
            func.count(
                func.distinct(Laureate.laureate_id)
            ).label("laureate_count")
        )
        .join(
            LaureatePrize,
            LaureatePrize.laureate_id == Laureate.laureate_id
        )
        .join(
            Prize,
            Prize.prize_id == LaureatePrize.prize_id
        )
        .join(
            Category,
            Category.category_id == Prize.category_id
        )
        .where(
            Category.name == category_name,
            Laureate.birth_country.is_not(None),
            Laureate.laureate_type == "Person"
        )
        .group_by(
            Laureate.birth_country
        )
        .order_by(
            func.count(
                func.distinct(Laureate.laureate_id)
            ).desc()
        )
    )

    return list(db.execute(statement).all())


def get_us_birth_state_counts_by_category(
    db: Session,
    category_name: str
) -> list[tuple[str, int]]:

    statement = (
        select(
            Laureate.birth_state,
            func.count(
                func.distinct(Laureate.laureate_id)
            ).label("laureate_count")
        )
        .join(
            LaureatePrize,
            LaureatePrize.laureate_id == Laureate.laureate_id
        )
        .join(
            Prize,
            Prize.prize_id == LaureatePrize.prize_id
        )
        .join(
            Category,
            Category.category_id == Prize.category_id
        )
        .where(
            Category.name == category_name,
            Laureate.birth_country == "USA",
            Laureate.birth_state.is_not(None),
            Laureate.laureate_type == "Person"
        )
        .group_by(
            Laureate.birth_state
        )
        .order_by(
            func.count(
                func.distinct(Laureate.laureate_id)
            ).desc()
        )
    )

    return list(db.execute(statement).all())

def get_institution_counts_by_category(
    db: Session,
    category_name: str,
    country: str
) -> list[tuple[str, int]]:

    statement = (
        select(
            Institution.name,
            func.count(
                func.distinct(LaureatePrize.laureate_id)
            ).label("laureate_count")
        )
        .join(
            AwardAffiliation,
            AwardAffiliation.institution_id == Institution.institution_id
        )
        .join(
            LaureatePrize,
            LaureatePrize.laureate_prize_id
            == AwardAffiliation.laureate_prize_id
        )
        .join(
            Prize,
            Prize.prize_id == LaureatePrize.prize_id
        )
        .join(
            Category,
            Category.category_id == Prize.category_id
        )
        .where(
            Category.name == category_name,
            Institution.country == country
        )
        .group_by(
            Institution.institution_id,
            Institution.name
        )
        .order_by(
            func.count(
                func.distinct(LaureatePrize.laureate_id)
            ).desc()
        )
    )

    return list(db.execute(statement).all())

def get_gender_counts_by_category(
    db: Session,
    category_name: str
) -> list[tuple[str, int]]:

    statement = (
        select(
            Laureate.gender,
            func.count(
                func.distinct(Laureate.laureate_id)
            ).label("laureate_count")
        )
        .join(
            LaureatePrize,
            LaureatePrize.laureate_id == Laureate.laureate_id
        )
        .join(
            Prize,
            Prize.prize_id == LaureatePrize.prize_id
        )
        .join(
            Category,
            Category.category_id == Prize.category_id
        )
        .where(
            Category.name == category_name,
            Laureate.laureate_type == "Person",
            Laureate.gender.is_not(None)
        )
        .group_by(
            Laureate.gender
        )
        .order_by(
            func.count(
                func.distinct(Laureate.laureate_id)
            ).desc()
        )
    )

    return list(db.execute(statement).all())

def get_laureate_counts_by_decade(
    db: Session,
    category: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None
) -> list[tuple[int, int]]:

    decade = (
        func.floor(Prize.year / 10) * 10
    ).label("decade")

    conditions = _year_range_conditions(start_year, end_year)

    statement = select(
        decade,
        func.count(
            func.distinct(Laureate.laureate_id)
        ).label("laureate_count")
    ).join(
        LaureatePrize,
        LaureatePrize.prize_id == Prize.prize_id
    ).join(
        Laureate,
        Laureate.laureate_id == LaureatePrize.laureate_id
    )

    if category is not None:
        statement = statement.join(
            Category,
            Category.category_id == Prize.category_id
        )
        conditions.append(Category.name == category)

    if conditions:
        statement = statement.where(*conditions)

    statement = statement.group_by(decade).order_by(decade)

    return list(db.execute(statement).all())

def get_average_age_at_award_by_category(
    db: Session,
    category_name: str
) -> float | None:
    """Average age-at-award OBSERVATIONS (approximate: Prize.year minus
    birth year), one per LaureatePrize row with a known birth date. No
    laureate-level DISTINCT is applied here, so a repeat winner in this
    category contributes one observation per award -- consistent with
    the age-distribution methodology in get_age_distribution().
    Organizations are excluded via laureate_type; missing birth dates
    are excluded via the IS NOT NULL filter below.
    """
    age_at_award = (
        Prize.year - func.year(Laureate.birth_date)
    )

    statement = (
        select(
            func.avg(age_at_award)
        )
        .join(
            LaureatePrize,
            LaureatePrize.prize_id == Prize.prize_id
        )
        .join(
            Laureate,
            Laureate.laureate_id == LaureatePrize.laureate_id
        )
        .join(
            Category,
            Category.category_id == Prize.category_id
        )
        .where(
            Category.name == category_name,
            Laureate.laureate_type == "Person",
            Laureate.birth_date.is_not(None)
        )
    )

    result = db.scalar(statement)

    return float(result) if result is not None else None


def get_categories_by_decade(
    db: Session,
    category: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None
) -> list[tuple[int, str, int]]:
    """Phase 10E trend: DISTINCT laureates within each category, per
    decade -- one row per (decade, category) combination that has at
    least one laureate. A repeat laureate winning the same category
    twice in the same decade is still one row's worth of count (distinct
    per decade+category, matching the locked laureates-by-category
    semantics); winning in two different decades or two different
    categories legitimately contributes to each combination.
    """
    decade = (
        func.floor(Prize.year / 10) * 10
    ).label("decade")

    conditions = _year_range_conditions(start_year, end_year)
    if category is not None:
        conditions.append(Category.name == category)

    statement = (
        select(
            decade,
            Category.name,
            func.count(
                func.distinct(Laureate.laureate_id)
            ).label("laureate_count")
        )
        .join(
            Prize,
            Prize.category_id == Category.category_id
        )
        .join(
            LaureatePrize,
            LaureatePrize.prize_id == Prize.prize_id
        )
        .join(
            Laureate,
            Laureate.laureate_id == LaureatePrize.laureate_id
        )
    )

    if conditions:
        statement = statement.where(*conditions)

    statement = statement.group_by(decade, Category.name).order_by(
        decade, Category.name
    )

    return list(db.execute(statement).all())

