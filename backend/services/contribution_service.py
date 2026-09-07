from sqlalchemy.orm import Session

from backend.models.contribution import Contribution
from backend.repositories import (
    contribution_repository,
    laureate_prize_repository,
    laureate_repository,
)
from backend.schemas.contribution import (
    ContributionCreate,
    ContributionDetailResponse,
    ContributionResponse,
    ContributionUpdate,
)
from backend.schemas.explanation import ExplanationResponse
from backend.services import connection_service
from backend.services.exceptions import ResourceNotFoundError, ServiceValidationError


def _validate_relationships(
    db: Session,
    laureate_id: int,
    contribution_type: str,
    laureate_prize_id: int | None,
) -> None:
    if laureate_repository.get_by_id(db, laureate_id) is None:
        raise ResourceNotFoundError("Laureate", laureate_id)

    if contribution_type == "NOBEL_LINKED":
        if laureate_prize_id is None:
            raise ServiceValidationError(
                "NOBEL_LINKED contributions require laureate_prize_id"
            )
        laureate_prize = laureate_prize_repository.get_by_id(
            db, laureate_prize_id
        )
        if laureate_prize is None:
            raise ResourceNotFoundError("LaureatePrize", laureate_prize_id)
        if laureate_prize.laureate_id != laureate_id:
            raise ServiceValidationError(
                "LaureatePrize does not belong to the contribution laureate"
            )
    elif laureate_prize_id is not None:
        raise ServiceValidationError(
            "BEYOND_NOBEL contributions cannot reference a LaureatePrize"
        )


def list_laureate_contributions(
    db: Session,
    laureate_id: int,
    contribution_type: str | None = None,
) -> list[Contribution]:
    if laureate_repository.get_by_id(db, laureate_id) is None:
        raise ResourceNotFoundError("Laureate", laureate_id)
    return contribution_repository.get_by_laureate(
        db, laureate_id, contribution_type
    )


def get_contribution(
    db: Session,
    contribution_id: int,
) -> ContributionDetailResponse:
    contribution = contribution_repository.get_detail_by_id(db, contribution_id)
    if contribution is None:
        raise ResourceNotFoundError("Contribution", contribution_id)
    return ContributionDetailResponse(
        contribution_id=contribution.contribution_id,
        laureate_id=contribution.laureate_id,
        laureate_prize_id=contribution.laureate_prize_id,
        contribution_type=contribution.contribution_type,
        title=contribution.title,
        summary=contribution.summary,
        significance=contribution.significance,
        source_url=contribution.source_url,
        explanations=[
            ExplanationResponse.model_validate(explanation)
            for explanation in contribution.explanations
        ],
        connections=[
            connection_service.to_response(connection)
            for connection in contribution.connections
        ],
    )


def create_contribution(db: Session, data: ContributionCreate) -> Contribution:
    _validate_relationships(
        db,
        data.laureate_id,
        data.contribution_type,
        data.laureate_prize_id,
    )
    return contribution_repository.create(db, Contribution(**data.model_dump()))


def update_contribution(
    db: Session,
    contribution_id: int,
    data: ContributionUpdate,
) -> Contribution:
    contribution = contribution_repository.get_by_id(db, contribution_id)
    if contribution is None:
        raise ResourceNotFoundError("Contribution", contribution_id)
    _validate_relationships(
        db,
        data.laureate_id,
        data.contribution_type,
        data.laureate_prize_id,
    )
    return contribution_repository.update(
        db,
        contribution,
        laureate_id=data.laureate_id,
        laureate_prize_id=data.laureate_prize_id,
        contribution_type=data.contribution_type,
        title=data.title,
        summary=data.summary,
        significance=data.significance,
        source_url=data.source_url,
    )
