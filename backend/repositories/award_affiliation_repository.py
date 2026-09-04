from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from backend.models.award_affiliation import AwardAffiliation
from backend.models.laureate_prize import LaureatePrize
from backend.models.prize import Prize


def get_by_id(
    db: Session,
    award_affiliation_id: int
) -> AwardAffiliation | None:
    statement = select(AwardAffiliation).where(
        AwardAffiliation.award_affiliation_id
        == award_affiliation_id
    )
    return db.scalar(statement)


def get_by_laureate_prize(
    db: Session,
    laureate_prize_id: int
) -> list[AwardAffiliation]:
    statement = select(AwardAffiliation).where(
        AwardAffiliation.laureate_prize_id
        == laureate_prize_id
    )
    return list(db.scalars(statement).all())


def get_by_institution(
    db: Session,
    institution_id: int
) -> list[AwardAffiliation]:
    statement = select(AwardAffiliation).where(
        AwardAffiliation.institution_id
        == institution_id
    )
    return list(db.scalars(statement).all())


def get_paginated_by_institution(
    db: Session,
    institution_id: int,
    limit: int,
    offset: int
) -> list[AwardAffiliation]:
    statement = (
        select(AwardAffiliation)
        .where(AwardAffiliation.institution_id == institution_id)
        .options(
            joinedload(AwardAffiliation.laureate_prize)
            .joinedload(LaureatePrize.laureate),
            joinedload(AwardAffiliation.laureate_prize)
            .joinedload(LaureatePrize.prize)
            .joinedload(Prize.category)
        )
        .order_by(AwardAffiliation.award_affiliation_id)
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def count_by_institution(db: Session, institution_id: int) -> int:
    statement = select(func.count()).select_from(
        AwardAffiliation
    ).where(AwardAffiliation.institution_id == institution_id)
    return db.scalar(statement) or 0


def get_by_laureate_prize_and_institution(
    db: Session,
    laureate_prize_id: int,
    institution_id: int
) -> AwardAffiliation | None:
    statement = select(AwardAffiliation).where(
        AwardAffiliation.laureate_prize_id == laureate_prize_id,
        AwardAffiliation.institution_id == institution_id
    )
    return db.scalar(statement)


def create(
    db: Session,
    award_affiliation: AwardAffiliation
) -> AwardAffiliation:
    db.add(award_affiliation)
    db.flush()
    db.refresh(award_affiliation)
    return award_affiliation
