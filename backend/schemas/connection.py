from typing import Literal

from pydantic import BaseModel, ConfigDict


ConnectionType = Literal[
    "APPLICATION",
    "EXPERIMENTAL_VALIDATION",
    "SCIENTIFIC_LEGACY",
]


class RelatedPrizeResponse(BaseModel):
    prize_id: int
    year: int
    category: str


class ConnectionBase(BaseModel):
    contribution_id: int
    connection_type: ConnectionType
    related_prize_id: int | None = None
    title: str
    description: str | None = None
    source_name: str | None = None
    source_url: str | None = None


class ConnectionCreate(ConnectionBase):
    pass


class ConnectionUpdate(ConnectionBase):
    pass


class ConnectionResponse(ConnectionBase):
    model_config = ConfigDict(from_attributes=True)

    connection_id: int
    related_prize: RelatedPrizeResponse | None = None
