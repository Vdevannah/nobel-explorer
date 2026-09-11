from sqlalchemy import func, select
from sqlalchemy.orm import Session, contains_eager, joinedload, selectinload

from backend.models.award_affiliation import AwardAffiliation
from backend.models.category import Category
from backend.models.laureate_prize import LaureatePrize
from backend.models.prize import Prize


def get_all(db: Session) -> list[Prize]:
    statement = select(Prize)
    return list(db.scalars(statement).all())


def get_paginated(
    db: Session,
    limit: int,
    offset: int,
    category: str | None = None,
    year: int | None = None
) -> list[Prize]:
    if category is not None:
        statement = (
            select(Prize)
            .join(Prize.category)
            .options(contains_eager(Prize.category))
            .where(Category.name == category)
        )
    else:
        statement = select(Prize).options(joinedload(Prize.category))
    if year is not None:
        statement = statement.where(Prize.year == year)
    statement = (
        statement
        .order_by(Prize.year, Prize.prize_id)
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def count_all(
    db: Session,
    category: str | None = None,
    year: int | None = None
) -> int:
    statement = select(func.count()).select_from(Prize)
    if category is not None:
        statement = statement.join(Prize.category).where(
            Category.name == category
        )
    if year is not None:
        statement = statement.where(Prize.year == year)
    return db.scalar(statement) or 0


def get_by_id(db: Session, prize_id: int) -> Prize | None:
    statement = select(Prize).where(
        Prize.prize_id == prize_id
    )
    return db.scalar(statement)


def get_detail_by_id(db: Session, prize_id: int) -> Prize | None:
    statement = (
        select(Prize)
        .where(Prize.prize_id == prize_id)
        .options(
            joinedload(Prize.category),
            selectinload(Prize.laureate_prizes)
            .selectinload(LaureatePrize.laureate),
            selectinload(Prize.laureate_prizes)
            .selectinload(LaureatePrize.award_affiliations)
            .selectinload(AwardAffiliation.institution)
        )
    )
    return db.scalar(statement)


def get_by_category(
    db: Session,
    category_id: int
) -> list[Prize]:
    statement = select(Prize).where(
        Prize.category_id == category_id
    )
    return list(db.scalars(statement).all())


def get_by_year_and_category(
    db: Session,
    year: int,
    category_id: int
) -> Prize | None:
    statement = select(Prize).where(
        Prize.year == year,
        Prize.category_id == category_id
    )
    return db.scalar(statement)


def create(db: Session, prize: Prize) -> Prize:
    db.add(prize)
    db.flush()
    db.refresh(prize)
    return prize
