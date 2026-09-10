from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.connection import ConnectionResponse
from backend.schemas.explanation import ExplanationResponse


ContributionType = Literal["NOBEL_LINKED", "BEYOND_NOBEL"]


class ContributionBase(BaseModel):
    contribution_type: ContributionType
    title: str
    summary: str | None = None
    significance: str | None = None
    source_url: str | None = None


class ContributionAttribution(BaseModel):
    laureate_id: int
    laureate_prize_id: int | None = None


class CreditedLaureate(ContributionAttribution):
    model_config = ConfigDict(from_attributes=True)

    name: str
    image_url: str | None


class ContributionCreate(ContributionBase):
    credited_laureates: list[ContributionAttribution] = Field(min_length=1)


class ContributionUpdate(ContributionCreate):
    pass


class ContributionResponse(ContributionBase):
    model_config = ConfigDict(from_attributes=True)

    contribution_id: int
    credited_laureates: list[CreditedLaureate]
    # Legacy projections: first credit by laureate_id, not ownership.
    laureate_id: int
    laureate_prize_id: int | None


class ContributionDetailResponse(ContributionResponse):
    explanations: list[ExplanationResponse] = Field(default_factory=list)
    connections: list[ConnectionResponse] = Field(default_factory=list)


class ContributionCatalogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contribution_id: int
    title: str
    summary: str | None
    contribution_type: ContributionType
    laureate_id: int
    credited_laureates: list[CreditedLaureate]
    laureate_name: str
    image_url: str | None
    category: str | None
    prize_year: int | None
    available_levels: list[str]
    quiz_available: bool
