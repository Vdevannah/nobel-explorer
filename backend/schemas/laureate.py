from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.prize import LaureateAwardResponse


class LaureateSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    laureate_id: int
    nobel_laureate_id: str
    full_name: str
    laureate_type: str
    birth_country: str | None
    gender: str | None
    featured: bool
    image_url: str | None


class LaureateDetailResponse(LaureateSummaryResponse):
    birth_date: date | None
    birth_city: str | None
    birth_state: str | None
    awards: list[LaureateAwardResponse] = Field(default_factory=list)


class PaginatedLaureatesResponse(BaseModel):
    items: list[LaureateSummaryResponse]
    total: int
    limit: int
    offset: int
