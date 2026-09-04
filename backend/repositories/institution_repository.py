from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.institution import Institution


def get_all(db: Session) -> list[Institution]:
    statement = select(Institution)
    return list(db.scalars(statement).all())


def get_paginated(
    db: Session,
    limit: int,
    offset: int
) -> list[Institution]:
    statement = (
        select(Institution)
        .order_by(Institution.institution_id)
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def count_all(db: Session) -> int:
    statement = select(func.count()).select_from(Institution)
    return db.scalar(statement) or 0


def get_by_id(
    db: Session,
    institution_id: int
) -> Institution | None:
    statement = select(Institution).where(
        Institution.institution_id == institution_id
    )
    return db.scalar(statement)


def get_by_name(
    db: Session,
    name: str
) -> Institution | None:
    statement = select(Institution).where(
        Institution.name == name
    )
    return db.scalar(statement)


def create(
    db: Session,
    institution: Institution
) -> Institution:
    db.add(institution)
    db.flush()
    db.refresh(institution)
    return institution
