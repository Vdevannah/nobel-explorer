from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.discovery import Discovery


def get_by_id(
    db: Session,
    discovery_id: int
) -> Discovery | None:
    statement = select(Discovery).where(
        Discovery.discovery_id == discovery_id
    )
    return db.scalar(statement)


def get_by_laureate_prize(
    db: Session,
    laureate_prize_id: int
) -> list[Discovery]:
    statement = select(Discovery).where(
        Discovery.laureate_prize_id == laureate_prize_id
    )
    return list(db.scalars(statement).all())


def create(
    db: Session,
    discovery: Discovery
) -> Discovery:
    db.add(discovery)
    db.flush()
    db.refresh(discovery)

    return discovery


def update(
    db: Session,
    discovery: Discovery,
    title: str,
    summary: str | None,
    significance: str | None,
    source_url: str | None
) -> Discovery:
    discovery.title = title
    discovery.summary = summary
    discovery.significance = significance
    discovery.source_url = source_url

    db.flush()
    db.refresh(discovery)

    return discovery


def delete(
    db: Session,
    discovery: Discovery
) -> None:
    db.delete(discovery)
    db.flush()