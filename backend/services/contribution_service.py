from sqlalchemy.orm import Session

from backend.models.contribution import Contribution
from backend.models.contribution_laureate import ContributionLaureate
from backend.repositories import (
    contribution_repository,
    laureate_prize_repository,
    laureate_repository,
)
from backend.schemas.contribution import (
    ContributionCatalogItem,
    ContributionAttribution,
    CreditedLaureate,
    ContributionCreate,
    ContributionDetailResponse,
    ContributionResponse,
    ContributionUpdate,
)
from backend.schemas.explanation import ExplanationResponse
from backend.services import connection_service
from backend.services.exceptions import ResourceNotFoundError, ServiceValidationError


LEVEL_ORDER = ["Simple", "Explore", "Advanced", "Expert"]


def _validate_relationships(
    db: Session,
    contribution_type: str,
    credited_laureates: list[ContributionAttribution],
) -> None:
    if not credited_laureates:
        raise ServiceValidationError("A contribution requires at least one credited laureate")
    ids = [credit.laureate_id for credit in credited_laureates]
    if len(ids) != len(set(ids)):
        raise ServiceValidationError("A laureate can only be credited once per contribution")
    for credit in credited_laureates:
        if laureate_repository.get_by_id(db, credit.laureate_id) is None:
            raise ResourceNotFoundError("Laureate", credit.laureate_id)
        if credit.laureate_prize_id is not None:
            award = laureate_prize_repository.get_by_id(db, credit.laureate_prize_id)
            if award is None:
                raise ResourceNotFoundError("LaureatePrize", credit.laureate_prize_id)
            if award.laureate_id != credit.laureate_id:
                raise ServiceValidationError("LaureatePrize does not belong to the credited laureate")
            if contribution_type == "BEYOND_NOBEL":
                raise ServiceValidationError("BEYOND_NOBEL contributions cannot reference a LaureatePrize")
    if contribution_type == "NOBEL_LINKED" and not any(
        credit.laureate_prize_id is not None for credit in credited_laureates
    ):
        raise ServiceValidationError("NOBEL_LINKED contributions require at least one award link")


def _credits(contribution: Contribution) -> list[CreditedLaureate]:
    return [
        CreditedLaureate.model_validate(credit)
        for credit in sorted(contribution.credited_laureates, key=lambda credit: credit.laureate_id)
    ]


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
        credited_laureates=_credits(contribution),
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


def list_catalog(db: Session) -> list[ContributionCatalogItem]:
    contributions = contribution_repository.list_catalog(db)
    catalog: list[ContributionCatalogItem] = []
    for contribution in contributions:
        credits = _credits(contribution)
        awards = [credit.laureate_prize.prize for credit in contribution.credited_laureates
                  if credit.laureate_prize is not None]
        # Keep the legacy award summary only when it is unambiguous.
        prize = awards[0] if awards and len({award.prize_id for award in awards}) == 1 else None
        category_name = prize.category.name if prize is not None else None
        prize_year = prize.year if prize is not None else None
        available_levels = sorted(
            {explanation.level for explanation in contribution.explanations},
            key=LEVEL_ORDER.index,
        )
        catalog.append(
            ContributionCatalogItem(
                contribution_id=contribution.contribution_id,
                title=contribution.title,
                summary=contribution.summary,
                contribution_type=contribution.contribution_type,
                laureate_id=contribution.laureate_id,
                credited_laureates=credits,
                laureate_name=credits[0].name,
                image_url=credits[0].image_url,
                category=category_name,
                prize_year=prize_year,
                available_levels=available_levels,
                quiz_available=len(contribution.quiz_questions) > 0,
            )
        )
    return catalog


def create_contribution(db: Session, data: ContributionCreate) -> Contribution:
    _validate_relationships(
        db,
        data.contribution_type,
        data.credited_laureates,
    )
    return contribution_repository.create(db, Contribution(
        **data.model_dump(exclude={"credited_laureates"}),
        credited_laureates=[ContributionLaureate(**credit.model_dump()) for credit in data.credited_laureates],
    ))


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
        data.contribution_type,
        data.credited_laureates,
    )
    return contribution_repository.update(
        db,
        contribution,
        credited_laureates=[ContributionLaureate(**credit.model_dump()) for credit in data.credited_laureates],
        contribution_type=data.contribution_type,
        title=data.title,
        summary=data.summary,
        significance=data.significance,
        source_url=data.source_url,
    )
