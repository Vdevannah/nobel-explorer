from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.models.connection import Connection
from backend.models.contribution import Contribution
from backend.models.contribution_laureate import ContributionLaureate
from backend.models.laureate_prize import LaureatePrize
from backend.models.prize import Prize


def get_by_id(db: Session, contribution_id: int) -> Contribution | None:
    statement = select(Contribution).where(
        Contribution.contribution_id == contribution_id
    )
    return db.scalar(statement)


def get_detail_by_id(db: Session, contribution_id: int) -> Contribution | None:
    statement = (
        select(Contribution)
        .where(Contribution.contribution_id == contribution_id)
        .options(
            selectinload(Contribution.explanations),
            selectinload(Contribution.connections)
            .selectinload(Connection.related_prize)
            .selectinload(Prize.category),
        )
    )
    return db.scalar(statement)


def list_catalog(db: Session) -> list[Contribution]:
    statement = (
        select(Contribution)
        .options(
            selectinload(Contribution.credited_laureates).selectinload(ContributionLaureate.laureate),
            selectinload(Contribution.credited_laureates).selectinload(ContributionLaureate.laureate_prize)
            .selectinload(LaureatePrize.prize)
            .selectinload(Prize.category),
            selectinload(Contribution.explanations),
            selectinload(Contribution.quiz_questions),
        )
        .order_by(Contribution.contribution_id)
    )
    return list(db.scalars(statement).all())


def get_by_laureate(
    db: Session,
    laureate_id: int,
    contribution_type: str | None = None,
) -> list[Contribution]:
    statement = select(Contribution).where(Contribution.credited_laureates.any(ContributionLaureate.laureate_id == laureate_id))
    if contribution_type is not None:
        statement = statement.where(
            Contribution.contribution_type == contribution_type
        )
    statement = statement.order_by(Contribution.contribution_id)
    return list(db.scalars(statement).all())


def get_by_laureate_prize(
    db: Session,
    laureate_prize_id: int,
) -> list[Contribution]:
    statement = select(Contribution).where(
        Contribution.credited_laureates.any(ContributionLaureate.laureate_prize_id == laureate_prize_id)
    )
    return list(db.scalars(statement).all())


def get_by_laureate_type_and_title(
    db: Session,
    laureate_id: int,
    contribution_type: str,
    title: str,
) -> Contribution | None:
    statement = select(Contribution).where(
        Contribution.credited_laureates.any(ContributionLaureate.laureate_id == laureate_id),
        Contribution.contribution_type == contribution_type,
        Contribution.title == title,
    )
    return db.scalar(statement)


def create(db: Session, contribution: Contribution) -> Contribution:
    db.add(contribution)
    db.flush()
    db.refresh(contribution)
    return contribution


def update(
    db: Session,
    contribution: Contribution,
    credited_laureates: list[ContributionLaureate],
    contribution_type: str,
    title: str,
    summary: str | None,
    significance: str | None,
    source_url: str | None,
) -> Contribution:
    existing = {credit.laureate_id: credit for credit in contribution.credited_laureates}
    updated = []
    for credit in credited_laureates:
        if credit.laureate_id in existing:
            current = existing[credit.laureate_id]
            current.laureate_prize_id = credit.laureate_prize_id
            updated.append(current)
        else:
            updated.append(credit)
    contribution.credited_laureates = updated
    contribution.contribution_type = contribution_type
    contribution.title = title
    contribution.summary = summary
    contribution.significance = significance
    contribution.source_url = source_url
    db.flush()
    db.refresh(contribution)
    return contribution


def delete(db: Session, contribution: Contribution) -> None:
    db.delete(contribution)
    db.flush()
