from sqlalchemy.orm import Session

from backend.models.connection import Connection
from backend.repositories import connection_repository, contribution_repository, prize_repository
from backend.schemas.connection import (
    ConnectionCreate,
    ConnectionResponse,
    ConnectionUpdate,
    RelatedPrizeResponse,
)
from backend.services.exceptions import ResourceNotFoundError, ServiceValidationError


def _validate_relationships(
    db: Session,
    contribution_id: int,
    connection_type: str,
    related_prize_id: int | None,
) -> None:
    if contribution_repository.get_by_id(db, contribution_id) is None:
        raise ResourceNotFoundError("Contribution", contribution_id)
    if related_prize_id is not None and connection_type != "SCIENTIFIC_LEGACY":
        raise ServiceValidationError(
            "related_prize_id is only allowed for SCIENTIFIC_LEGACY connections"
        )
    if (
        related_prize_id is not None
        and prize_repository.get_by_id(db, related_prize_id) is None
    ):
        raise ResourceNotFoundError("Prize", related_prize_id)


def to_response(connection: Connection) -> ConnectionResponse:
    related_prize = None
    if connection.related_prize is not None:
        related_prize = RelatedPrizeResponse(
            prize_id=connection.related_prize.prize_id,
            year=connection.related_prize.year,
            category=connection.related_prize.category.name,
        )
    return ConnectionResponse(
        connection_id=connection.connection_id,
        contribution_id=connection.contribution_id,
        connection_type=connection.connection_type,
        related_prize_id=connection.related_prize_id,
        title=connection.title,
        description=connection.description,
        source_name=connection.source_name,
        source_url=connection.source_url,
        related_prize=related_prize,
    )


def list_connections(db: Session, contribution_id: int) -> list[ConnectionResponse]:
    if contribution_repository.get_by_id(db, contribution_id) is None:
        raise ResourceNotFoundError("Contribution", contribution_id)
    return [
        to_response(connection)
        for connection in connection_repository.get_by_contribution(
            db, contribution_id
        )
    ]


def create_connection(db: Session, data: ConnectionCreate) -> Connection:
    _validate_relationships(
        db, data.contribution_id, data.connection_type, data.related_prize_id
    )
    return connection_repository.create(db, Connection(**data.model_dump()))


def update_connection(
    db: Session,
    connection_id: int,
    data: ConnectionUpdate,
) -> Connection:
    connection = connection_repository.get_by_id(db, connection_id)
    if connection is None:
        raise ResourceNotFoundError("Connection", connection_id)
    _validate_relationships(
        db, data.contribution_id, data.connection_type, data.related_prize_id
    )
    connection.contribution_id = data.contribution_id
    return connection_repository.update(
        db,
        connection,
        connection_type=data.connection_type,
        title=data.title,
        description=data.description,
        source_name=data.source_name,
        source_url=data.source_url,
        related_prize_id=data.related_prize_id,
    )
