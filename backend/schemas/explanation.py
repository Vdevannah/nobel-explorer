from typing import Literal

from pydantic import BaseModel, ConfigDict


ExplanationLevel = Literal["Simple", "Explore", "Advanced", "Expert"]


class ExplanationBase(BaseModel):
    contribution_id: int
    level: ExplanationLevel
    explanation_text: str
    key_concepts: str | None = None


class ExplanationCreate(ExplanationBase):
    pass


class ExplanationUpdate(ExplanationBase):
    pass


class ExplanationResponse(ExplanationBase):
    model_config = ConfigDict(from_attributes=True)

    explanation_id: int
