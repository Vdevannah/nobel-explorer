from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.prize import Prize


def get_all(db: Session) -> list[Prize]:
    statement = select(Prize)
    return list(db.scalars(statement).all())


def get_by_id(db: Session, prize_id: int) -> Prize | None:
    statement = select(Prize).where(
        Prize.prize_id == prize_id
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