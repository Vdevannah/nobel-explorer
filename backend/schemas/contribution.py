from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.connection import ConnectionResponse
from backend.schemas.explanation import ExplanationResponse


ContributionType = Literal["NOBEL_LINKED", "BEYOND_NOBEL"]


class ContributionBase(BaseModel):
    laureate_id: int
    laureate_prize_id: int | None = None
    contribution_type: ContributionType
    title: str
    summary: str | None = None
    significance: str | None = None
    source_url: str | None = None


class ContributionCreate(ContributionBase):
    pass


class ContributionUpdate(ContributionBase):
    pass


class ContributionResponse(ContributionBase):
    model_config = ConfigDict(from_attributes=True)

    contribution_id: int


class ContributionDetailResponse(ContributionResponse):
    explanations: list[ExplanationResponse] = Field(default_factory=list)
    connections: list[ConnectionResponse] = Field(default_factory=list)
