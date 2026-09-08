from sqlalchemy import case, select, func
from sqlalchemy.orm import Session

from backend.models.category import Category
from backend.models.prize import Prize
from backend.models.laureate import Laureate
from backend.models.laureate_prize import LaureatePrize
from backend.models.institution import Institution
from backend.models.award_affiliation import AwardAffiliation


def count_total_laureates(db: Session) -> int:
    statement = select(
        func.count(Laureate.laureate_id)
    )

    return db.scalar(statement) or 0


def count_total_prizes(db: Session) -> int:
    statement = select(
        func.count(Prize.prize_id)
    )

    return db.scalar(statement) or 0


def count_distinct_birth_countries(db: Session) -> int:
    statement = (
        select(
            func.count(func.distinct(Laureate.birth_country))
        )
        .where(
            Laureate.birth_country.is_not(None),
            Laureate.laureate_type == "Person"
        )
    )

    return db.scalar(statement) or 0


def get_overall_gender_counts(db: Session) -> list[tuple[str, int]]:
    statement = (
        select(
            Laureate.gender,
            func.count(
                func.distinct(Laureate.laureate_id)
            ).label("laureate_count")
        )
        .where(
            Laureate.laureate_type == "Person",
            Laureate.gender.is_not(None)
        )
        .group_by(Laureate.gender)
    )

    return list(db.execute(statement).all())


def get_top_birth_countries(
    db: Session,
    limit: int = 5
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
        .where(
            Laureate.birth_country.is_not(None),
            Laureate.laureate_type == "Person"
        )
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
    db: Session
) -> list[tuple[int, int]]:

    decade = (
        func.floor(Prize.year / 10) * 10
    ).label("decade")

    statement = (
        select(
            decade,
            func.count(
                func.distinct(Prize.prize_id)
            ).label("prize_count")
        )
        .group_by(decade)
        .order_by(decade)
    )

    return list(db.execute(statement).all())


def get_age_distribution(db: Session) -> list[tuple[str, int]]:
    """Bucket age-at-award OBSERVATIONS (one per LaureatePrize row with a
    known birth date), not distinct laureates. A repeat winner with a
    known birth date contributes one observation per award, and those
    observations may land in different age groups if the awards came at
    different ages -- this is intentional (Phase 10F methodology), not a
    double-count bug. Counting `LaureatePrize.laureate_prize_id` (the
    join's own primary key) rather than `Laureate.laureate_id` is what
    makes each award count as its own observation.
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
        .where(
            Laureate.laureate_type == "Person",
            Laureate.birth_date.is_not(None)
        )
        .group_by(age_group)
    )

    return list(db.execute(statement).all())


def get_gender_counts_by_era(
    db: Session
) -> list[tuple[str, str, int]]:
    """Count DISTINCT person laureates with known gender per era, not
    award observations: a laureate who won twice within the same era is
    still one person in that era's denominator. Organizations and
    unknown-gender records are excluded entirely (never counted, and
    never treated as a gender). This is the locked women-by-era
    methodology from Phase 10C/10F and is unchanged from prior phases.
    """
    era = case(
        (Prize.year <= 1950, "1901-1950"),
        (Prize.year <= 1970, "1951-1970"),
        (Prize.year <= 1990, "1971-1990"),
        (Prize.year <= 2010, "1991-2010"),
        else_="2011-present"
    ).label("era")

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
        .where(
            Laureate.laureate_type == "Person",
            Laureate.gender.is_not(None)
        )
        .group_by(era, Laureate.gender)
    )

    return list(db.execute(statement).all())


def get_laureate_counts_by_category(
    db: Session
) -> list[tuple[str, int]]:

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
        .group_by(Category.name)
        .order_by(
            func.count(
                func.distinct(Laureate.laureate_id)
            ).desc()
        )
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
    db: Session
) -> list[tuple[int, int]]:

    decade = (
        func.floor(Prize.year / 10) * 10
    ).label("decade")

    statement = (
        select(
            decade,
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
        .group_by(decade)
        .order_by(decade)
    )

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

