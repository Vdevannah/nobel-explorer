from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.laureate import Laureate


def get_all(db: Session) -> list[Laureate]:
    statement = select(Laureate)
    return list(db.scalars(statement).all())


def get_by_id(
    db: Session,
    laureate_id: int
) -> Laureate | None:
    statement = select(Laureate).where(
        Laureate.laureate_id == laureate_id
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