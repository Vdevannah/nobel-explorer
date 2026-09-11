from sqlalchemy.orm import Session

from backend.repositories import prize_repository
from backend.schemas.institution import InstitutionResponse
from backend.schemas.prize import (
    PaginatedPrizesResponse,
    PrizeDetailResponse,
    PrizeLaureateResponse,
)
from backend.services.exceptions import ResourceNotFoundError


def list_prizes(
    db: Session,
    limit: int,
    offset: int,
    category: str | None = None,
    year: int | None = None
) -> PaginatedPrizesResponse:
    prizes = prize_repository.get_paginated(
        db, limit, offset, category, year
    )
    total = prize_repository.count_all(db, category, year)

    return PaginatedPrizesResponse(
        items=prizes,
        total=total,
        limit=limit,
        offset=offset
    )


def get_prize(db: Session, prize_id: int) -> PrizeDetailResponse:
    prize = prize_repository.get_detail_by_id(db, prize_id)

    if prize is None:
        raise ResourceNotFoundError("Prize", prize_id)

    laureates = []

    for laureate_prize in sorted(
        prize.laureate_prizes,
        key=lambda item: item.laureate_id
    ):
        laureate = laureate_prize.laureate
        affiliations = [
            InstitutionResponse.model_validate(
                award_affiliation.institution
            )
            for award_affiliation in laureate_prize.award_affiliations
        ]
        laureates.append(
            PrizeLaureateResponse(
                laureate_id=laureate.laureate_id,
                nobel_laureate_id=laureate.nobel_laureate_id,
                full_name=laureate.full_name,
                laureate_type=laureate.laureate_type,
                prize_share=laureate_prize.prize_share,
                motivation=laureate_prize.motivation,
                affiliations=affiliations
            )
        )

    return PrizeDetailResponse(
        prize_id=prize.prize_id,
        year=prize.year,
        category=prize.category,
        laureates=laureates
    )
