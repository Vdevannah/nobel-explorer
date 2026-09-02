from sqlalchemy import select, func
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
            Laureate.birth_country == "United States",
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

