from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.laureate_prize import LaureatePrize


def get_by_id(
    db: Session,
    laureate_prize_id: int
) -> LaureatePrize | None:
    statement = select(LaureatePrize).where(
        LaureatePrize.laureate_prize_id == laureate_prize_id
    )
    return db.scalar(statement)


def get_by_laureate(
    db: Session,
    laureate_id: int
) -> list[LaureatePrize]:
    statement = select(LaureatePrize).where(
        LaureatePrize.laureate_id == laureate_id
    )
    return list(db.scalars(statement).all())


def get_by_prize(
    db: Session,
    prize_id: int
) -> list[LaureatePrize]:
    statement = select(LaureatePrize).where(
        LaureatePrize.prize_id == prize_id
    )
    return list(db.scalars(statement).all())


def get_by_laureate_and_prize(
    db: Session,
    laureate_id: int,
    prize_id: int
) -> LaureatePrize | None:
    statement = select(LaureatePrize).where(
        LaureatePrize.laureate_id == laureate_id,
        LaureatePrize.prize_id == prize_id
    )
    return db.scalar(statement)


def create(
    db: Session,
    laureate_prize: LaureatePrize
) -> LaureatePrize:
    db.add(laureate_prize)
    db.flush()
    db.refresh(laureate_prize)
    return laureate_prize
