from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.models.connection import Connection
from backend.models.contribution import Contribution
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


def get_by_laureate(
    db: Session,
    laureate_id: int,
    contribution_type: str | None = None,
) -> list[Contribution]:
    statement = select(Contribution).where(Contribution.laureate_id == laureate_id)
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
        Contribution.laureate_prize_id == laureate_prize_id
    )
    return list(db.scalars(statement).all())


def get_by_laureate_type_and_title(
    db: Session,
    laureate_id: int,
    contribution_type: str,
    title: str,
) -> Contribution | None:
    statement = select(Contribution).where(
        Contribution.laureate_id == laureate_id,
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
    laureate_id: int,
    laureate_prize_id: int | None,
    contribution_type: str,
    title: str,
    summary: str | None,
    significance: str | None,
    source_url: str | None,
) -> Contribution:
    contribution.laureate_id = laureate_id
    contribution.laureate_prize_id = laureate_prize_id
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
