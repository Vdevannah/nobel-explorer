from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.award_affiliation import AwardAffiliation


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
