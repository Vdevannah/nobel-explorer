from pydantic import BaseModel, ConfigDict

from backend.schemas.category import CategoryResponse


class InstitutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    institution_id: int
    name: str
    city: str | None
    state: str | None
    country: str | None


class PaginatedInstitutionsResponse(BaseModel):
    items: list[InstitutionResponse]
    total: int
    limit: int
    offset: int


class InstitutionAwardResponse(BaseModel):
    award_affiliation_id: int
    laureate_prize_id: int
    laureate_id: int
    nobel_laureate_id: str
    full_name: str
    prize_id: int
    year: int
    category: CategoryResponse
    prize_share: str | None
    motivation: str | None


class PaginatedInstitutionAwardsResponse(BaseModel):
    items: list[InstitutionAwardResponse]
    total: int
    limit: int
    offset: int
