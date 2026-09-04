from sqlalchemy.orm import Session

from backend.repositories import (
    award_affiliation_repository,
    institution_repository,
)
from backend.schemas.institution import (
    InstitutionAwardResponse,
    InstitutionResponse,
    PaginatedInstitutionAwardsResponse,
    PaginatedInstitutionsResponse,
)
from backend.services.exceptions import ResourceNotFoundError


def list_institutions(
    db: Session,
    limit: int,
    offset: int
) -> PaginatedInstitutionsResponse:
    institutions = institution_repository.get_paginated(db, limit, offset)
    total = institution_repository.count_all(db)

    return PaginatedInstitutionsResponse(
        items=institutions,
        total=total,
        limit=limit,
        offset=offset
    )


def get_institution(
    db: Session,
    institution_id: int
) -> InstitutionResponse:
    institution = institution_repository.get_by_id(db, institution_id)

    if institution is None:
        raise ResourceNotFoundError("Institution", institution_id)

    return InstitutionResponse.model_validate(institution)


def list_institution_awards(
    db: Session,
    institution_id: int,
    limit: int,
    offset: int
) -> PaginatedInstitutionAwardsResponse:
    if institution_repository.get_by_id(db, institution_id) is None:
        raise ResourceNotFoundError("Institution", institution_id)

    award_affiliations = (
        award_affiliation_repository.get_paginated_by_institution(
            db,
            institution_id,
            limit,
            offset
        )
    )
    total = award_affiliation_repository.count_by_institution(
        db,
        institution_id
    )
    items = []

    for award_affiliation in award_affiliations:
        laureate_prize = award_affiliation.laureate_prize
        laureate = laureate_prize.laureate
        prize = laureate_prize.prize
        items.append(
            InstitutionAwardResponse(
                award_affiliation_id=(
                    award_affiliation.award_affiliation_id
                ),
                laureate_prize_id=laureate_prize.laureate_prize_id,
                laureate_id=laureate.laureate_id,
                nobel_laureate_id=laureate.nobel_laureate_id,
                full_name=laureate.full_name,
                prize_id=prize.prize_id,
                year=prize.year,
                category=prize.category,
                prize_share=laureate_prize.prize_share,
                motivation=laureate_prize.motivation
            )
        )

    return PaginatedInstitutionAwardsResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset
    )
