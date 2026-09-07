from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.models.connection import Connection
from backend.models.prize import Prize


def get_by_id(db: Session, connection_id: int) -> Connection | None:
    statement = (
        select(Connection)
        .where(Connection.connection_id == connection_id)
        .options(
            joinedload(Connection.related_prize).joinedload(Prize.category)
        )
    )
    return db.scalar(statement)


def get_by_contribution(db: Session, contribution_id: int) -> list[Connection]:
    statement = (
        select(Connection)
        .where(Connection.contribution_id == contribution_id)
        .options(
            joinedload(Connection.related_prize).joinedload(Prize.category)
        )
        .order_by(Connection.connection_id)
    )
    return list(db.scalars(statement).all())


def get_by_contribution_type_and_title(
    db: Session,
    contribution_id: int,
    connection_type: str,
    title: str,
) -> Connection | None:
    statement = select(Connection).where(
        Connection.contribution_id == contribution_id,
        Connection.connection_type == connection_type,
        Connection.title == title,
    )
    return db.scalar(statement)


def create(db: Session, connection: Connection) -> Connection:
    db.add(connection)
    db.flush()
    db.refresh(connection)
    return connection


def update(
    db: Session,
    connection: Connection,
    connection_type: str,
    title: str,
    description: str | None,
    source_name: str | None,
    source_url: str | None,
    related_prize_id: int | None,
) -> Connection:
    connection.connection_type = connection_type
    connection.title = title
    connection.description = description
    connection.source_name = source_name
    connection.source_url = source_url
    connection.related_prize_id = related_prize_id
    db.flush()
    db.refresh(connection)
    return connection


def delete(db: Session, connection: Connection) -> None:
    db.delete(connection)
    db.flush()
