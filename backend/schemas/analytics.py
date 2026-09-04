from pydantic import BaseModel


class AnalyticsSummaryResponse(BaseModel):
    total_laureates: int
    total_prizes: int


class CategoryCountResponse(BaseModel):
    category: str
    laureate_count: int


class CountryCountResponse(BaseModel):
    country: str
    laureate_count: int


class StateCountResponse(BaseModel):
    state: str
    laureate_count: int


class InstitutionCountResponse(BaseModel):
    institution: str
    laureate_count: int


class GenderCountResponse(BaseModel):
    gender: str
    laureate_count: int


class DecadeCountResponse(BaseModel):
    decade: int
    laureate_count: int


class AverageAgeResponse(BaseModel):
    category: str
    average_age: float | None
