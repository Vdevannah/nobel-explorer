from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.models.award_affiliation import AwardAffiliation
from backend.models.category import Category
from backend.models.laureate import Laureate
from backend.models.laureate_prize import LaureatePrize
from backend.models.prize import Prize


def get_all(db: Session) -> list[Laureate]:
    statement = select(Laureate)
    return list(db.scalars(statement).all())


def get_paginated(
    db: Session,
    limit: int,
    offset: int,
    category: str | None = None,
    year: int | None = None,
    country: str | None = None,
    gender: str | None = None,
    search: str | None = None
) -> list[Laureate]:
    statement = select(Laureate)

    if category is not None or year is not None:
        statement = statement.join(Laureate.laureate_prizes).join(
            LaureatePrize.prize
        )

    if category is not None:
        statement = statement.join(Prize.category).where(
            Category.name == category
        )

    if year is not None:
        statement = statement.where(Prize.year == year)

    if country is not None:
        statement = statement.where(Laureate.birth_country == country)

    if gender is not None:
        statement = statement.where(Laureate.gender == gender)

    search_term = search.strip() if search is not None else ""
    if search_term:
        statement = statement.where(
            Laureate.full_name.ilike(f"%{search_term}%")
        )

    statement = (
        statement.distinct()
        .order_by(Laureate.laureate_id)
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def count_all(
    db: Session,
    category: str | None = None,
    year: int | None = None,
    country: str | None = None,
    gender: str | None = None,
    search: str | None = None
) -> int:
    statement = select(
        func.count(func.distinct(Laureate.laureate_id))
    ).select_from(Laureate)

    if category is not None or year is not None:
        statement = statement.join(Laureate.laureate_prizes).join(
            LaureatePrize.prize
        )

    if category is not None:
        statement = statement.join(Prize.category).where(
            Category.name == category
        )

    if year is not None:
        statement = statement.where(Prize.year == year)

    if country is not None:
        statement = statement.where(Laureate.birth_country == country)

    if gender is not None:
        statement = statement.where(Laureate.gender == gender)

    search_term = search.strip() if search is not None else ""
    if search_term:
        statement = statement.where(
            Laureate.full_name.ilike(f"%{search_term}%")
        )

    return db.scalar(statement) or 0


def get_by_id(
    db: Session,
    laureate_id: int
) -> Laureate | None:
    statement = select(Laureate).where(
        Laureate.laureate_id == laureate_id
    )
    return db.scalar(statement)


def get_detail_by_id(
    db: Session,
    laureate_id: int
) -> Laureate | None:
    statement = (
        select(Laureate)
        .where(Laureate.laureate_id == laureate_id)
        .options(
            selectinload(Laureate.laureate_prizes)
            .selectinload(LaureatePrize.prize)
            .selectinload(Prize.category),
            selectinload(Laureate.laureate_prizes)
            .selectinload(LaureatePrize.award_affiliations)
            .selectinload(AwardAffiliation.institution)
        )
    )
    return db.scalar(statement)


def get_by_nobel_id(
    db: Session,
    nobel_laureate_id: str
) -> Laureate | None:
    statement = select(Laureate).where(
        Laureate.nobel_laureate_id == nobel_laureate_id
    )
    return db.scalar(statement)


def get_featured(db: Session) -> list[Laureate]:
    statement = select(Laureate).where(
        Laureate.featured.is_(True)
    )
    return list(db.scalars(statement).all())


def create(db: Session, laureate: Laureate) -> Laureate:
    db.add(laureate)
    db.flush()
    db.refresh(laureate)
    return laureate
