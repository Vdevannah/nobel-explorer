from sqlalchemy.orm import Session

from backend.models.laureate import Laureate
from backend.repositories import laureate_repository
from backend.schemas.institution import InstitutionResponse
from backend.schemas.laureate import (
    LaureateDetailResponse,
    PaginatedLaureatesResponse,
)
from backend.schemas.prize import LaureateAwardResponse, PrizeSummaryResponse
from backend.services.exceptions import ResourceNotFoundError


def list_laureates(
    db: Session,
    limit: int,
    offset: int,
    category: str | None = None,
    year: int | None = None,
    country: str | None = None,
    gender: str | None = None,
    search: str | None = None
) -> PaginatedLaureatesResponse:
    laureates = laureate_repository.get_paginated(
        db,
        limit,
        offset,
        category,
        year,
        country,
        gender,
        search
    )
    total = laureate_repository.count_all(
        db,
        category,
        year,
        country,
        gender,
        search
    )

    return PaginatedLaureatesResponse(
        items=laureates,
        total=total,
        limit=limit,
        offset=offset
    )


def get_laureate(
    db: Session,
    laureate_id: int
) -> LaureateDetailResponse:
    laureate = laureate_repository.get_detail_by_id(db, laureate_id)

    if laureate is None:
        raise ResourceNotFoundError("Laureate", laureate_id)

    awards = []

    for laureate_prize in sorted(
        laureate.laureate_prizes,
        key=lambda item: item.prize.year
    ):
        affiliations = [
            InstitutionResponse.model_validate(
                award_affiliation.institution
            )
            for award_affiliation in laureate_prize.award_affiliations
        ]
        awards.append(
            LaureateAwardResponse(
                laureate_prize_id=laureate_prize.laureate_prize_id,
                prize=PrizeSummaryResponse.model_validate(
                    laureate_prize.prize
                ),
                prize_share=laureate_prize.prize_share,
                motivation=laureate_prize.motivation,
                affiliations=affiliations
            )
        )

    return LaureateDetailResponse(
        laureate_id=laureate.laureate_id,
        nobel_laureate_id=laureate.nobel_laureate_id,
        full_name=laureate.full_name,
        laureate_type=laureate.laureate_type,
        birth_country=laureate.birth_country,
        gender=laureate.gender,
        featured=laureate.featured,
        image_url=laureate.image_url,
        birth_date=laureate.birth_date,
        birth_city=laureate.birth_city,
        birth_state=laureate.birth_state,
        awards=awards
    )


def get_laureate_by_nobel_id(
    db: Session,
    nobel_laureate_id: str
) -> Laureate:
    laureate = laureate_repository.get_by_nobel_id(
        db,
        nobel_laureate_id
    )

    if laureate is None:
        raise ResourceNotFoundError("Laureate", nobel_laureate_id)

    return laureate


def get_featured_laureates(db: Session) -> list[Laureate]:
    return laureate_repository.get_featured(db)
