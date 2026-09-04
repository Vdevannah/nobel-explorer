from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.category import CategoryResponse
from backend.schemas.institution import InstitutionResponse


class PrizeSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    prize_id: int
    year: int
    category: CategoryResponse


class LaureateAwardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    laureate_prize_id: int
    prize: PrizeSummaryResponse
    prize_share: str | None
    motivation: str | None
    affiliations: list[InstitutionResponse] = Field(default_factory=list)


class PrizeLaureateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    laureate_id: int
    nobel_laureate_id: str
    full_name: str
    laureate_type: str
    prize_share: str | None
    motivation: str | None
    affiliations: list[InstitutionResponse] = Field(default_factory=list)


class PrizeDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    prize_id: int
    year: int
    category: CategoryResponse
    laureates: list[PrizeLaureateResponse] = Field(default_factory=list)


class PaginatedPrizesResponse(BaseModel):
    items: list[PrizeSummaryResponse]
    total: int
    limit: int
    offset: int
