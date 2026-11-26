"""Typed, validated argument schemas for the four Nobel tools.

These Pydantic models are the single source of truth for tool arguments:
LangChain derives each tool's JSON schema from them, and the plain Python
functions re-validate through them, so the same rules apply with or without
an LLM. All models forbid unknown fields.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from backend.ai.config import EDUCATIONAL_LEVELS

FIRST_PRIZE_YEAR = 1901
CURRENT_YEAR = date.today().year

NOBEL_CATEGORIES: tuple[str, ...] = (
    "Chemistry",
    "Economic Sciences",
    "Literature",
    "Peace",
    "Physics",
    "Physiology or Medicine",
)
NobelCategory = Literal[
    "Chemistry", "Economic Sciences", "Literature", "Peace", "Physics", "Physiology or Medicine",
]

# Deterministic, documented aliases (lower-case key -> canonical name).
CATEGORY_ALIASES: dict[str, str] = {
    **{name.lower(): name for name in NOBEL_CATEGORIES},
    "economics": "Economic Sciences",
    "economic science": "Economic Sciences",
    "economy": "Economic Sciences",
    "medicine": "Physiology or Medicine",
    "physiology": "Physiology or Medicine",
    "physiology and medicine": "Physiology or Medicine",
}

# Stored birth/affiliation country names follow the Nobel Prize API
# (e.g. "USA", "United Kingdom", "the Netherlands"). Only unambiguous
# synonyms are mapped; historical names (e.g. "Russian Empire") are not.
COUNTRY_ALIASES: dict[str, str] = {
    "united states": "USA",
    "united states of america": "USA",
    "us": "USA",
    "u.s.": "USA",
    "u.s.a.": "USA",
    "america": "USA",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "great britain": "United Kingdom",
    "britain": "United Kingdom",
    "netherlands": "the Netherlands",
    "holland": "the Netherlands",
}

GENDER_ALIASES = {"female": "female", "woman": "female", "women": "female",
                  "male": "male", "man": "male", "men": "male"}

_FORBIDDEN_TEXT = re.compile(r"[%_\\\x00-\x1f\x7f]")


# --------------------------------------------------------------------------
# Reusable field validators
# NOTE: in Annotated[...] put Field(...) constraints BEFORE BeforeValidator, otherwise
# Pydantic emits non-standard "ge"/"le" keys instead of JSON Schema minimum/maximum.
# --------------------------------------------------------------------------

def _reject_bool(value: Any) -> Any:
    if isinstance(value, bool):
        raise ValueError("must be an integer, not a boolean")
    return value


def _normalise_category(value: Any) -> Any:
    if value is None or not isinstance(value, str):
        return value
    key = " ".join(value.split()).lower()
    if key in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[key]
    hint = " There is no Nobel Prize in Mathematics." if "math" in key else ""
    raise ValueError(
        f"'{value}' is not a Nobel Prize category. Valid categories: {', '.join(NOBEL_CATEGORIES)}.{hint}"
    )


def _normalise_level(value: Any) -> Any:
    if value is None or not isinstance(value, str):
        return value
    lookup = {name.lower(): name for name in EDUCATIONAL_LEVELS}
    canonical = lookup.get(value.strip().lower())
    if canonical is None:
        raise ValueError(f"level must be one of {', '.join(EDUCATIONAL_LEVELS)}")
    return canonical


def _normalise_gender(value: Any) -> Any:
    if value is None or not isinstance(value, str):
        return value
    canonical = GENDER_ALIASES.get(value.strip().lower())
    if canonical is None:
        raise ValueError("gender must be 'female' or 'male' (organizations have no gender)")
    return canonical


def _safe_text(value: Any) -> Any:
    if isinstance(value, str):
        value = " ".join(value.split())
        if _FORBIDDEN_TEXT.search(value):
            raise ValueError("must not contain %, _, backslashes or control characters")
    return value


def _normalise_country(value: Any) -> Any:
    value = _safe_text(value)
    if isinstance(value, str):
        return COUNTRY_ALIASES.get(value.lower(), value)
    return value


Year = Annotated[int, Field(ge=FIRST_PRIZE_YEAR, le=CURRENT_YEAR), BeforeValidator(_reject_bool)]
PositiveId = Annotated[int, Field(ge=1, le=2_000_000_000), BeforeValidator(_reject_bool)]
Category = Annotated[NobelCategory, BeforeValidator(_normalise_category)]
Level = Annotated[
    Literal["Simple", "Explore", "Advanced", "Expert"], BeforeValidator(_normalise_level)
]
Gender = Annotated[Literal["female", "male"], BeforeValidator(_normalise_gender)]
Country = Annotated[str, Field(min_length=2, max_length=60), BeforeValidator(_normalise_country)]


class _ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# --------------------------------------------------------------------------
# search_laureates
# --------------------------------------------------------------------------

class SearchLaureatesInput(_ToolInput):
    """Exact, structured laureate lookup. At least one filter is required."""

    name: Annotated[str, Field(min_length=2, max_length=100), BeforeValidator(_safe_text)] | None = Field(
        default=None,
        description="Case-insensitive substring of the laureate's full name, e.g. 'Curie' or 'Bertozzi'.",
    )
    year: Year | None = Field(default=None, description=f"Nobel Prize award year ({FIRST_PRIZE_YEAR}-{CURRENT_YEAR}).")
    category: Category | None = Field(
        default=None,
        description="Nobel Prize category. Aliases such as 'Medicine' and 'Economics' are accepted.",
    )
    birth_country: Country | None = Field(
        default=None,
        description=(
            "Country of BIRTH as recorded by the Nobel Prize API (e.g. 'USA', 'United Kingdom', "
            "'the Netherlands'). This is NOT the country of the award-time affiliation."
        ),
    )
    gender: Gender | None = Field(default=None, description="'female' or 'male'. Organizations have no gender.")
    limit: Annotated[int, Field(ge=1, le=20), BeforeValidator(_reject_bool)] = Field(
        default=10, description="Maximum laureates to return (1-20)."
    )

    @model_validator(mode="after")
    def _require_a_filter(self) -> "SearchLaureatesInput":
        if not any((self.name, self.year, self.category, self.birth_country, self.gender)):
            raise ValueError("provide at least one of: name, year, category, birth_country, gender")
        return self


# --------------------------------------------------------------------------
# get_laureate_details
# --------------------------------------------------------------------------

class LaureateDetailsInput(_ToolInput):
    laureate_id: PositiveId = Field(
        description="Internal Nobel Explorer laureate_id returned by search_laureates (not the Nobel API id).",
    )
    include_explanation_level: Level | None = Field(
        default=None,
        description=(
            "Optionally include the full educational explanation at this level "
            "(Simple, Explore, Advanced, Expert) for each of the laureate's contributions."
        ),
    )


# --------------------------------------------------------------------------
# get_nobel_statistics
# --------------------------------------------------------------------------

StatisticOperation = Literal[
    "summary",
    "laureates_by_category",
    "laureates_by_gender",
    "prizes_by_decade",
    "laureates_by_decade",
    "top_birth_countries",
    "women_by_era",
    "average_age_at_award",
    "laureates_by_affiliation_institution",
]

# operation -> (allowed filters, required filters)
OPERATION_FILTERS: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "summary": (frozenset({"category", "start_year", "end_year"}), frozenset()),
    "laureates_by_category": (frozenset({"start_year", "end_year"}), frozenset()),
    "laureates_by_gender": (frozenset({"category", "start_year", "end_year"}), frozenset()),
    "prizes_by_decade": (frozenset({"category", "start_year", "end_year"}), frozenset()),
    "laureates_by_decade": (frozenset({"category", "start_year", "end_year"}), frozenset()),
    "top_birth_countries": (frozenset({"category", "start_year", "end_year", "limit"}), frozenset()),
    "women_by_era": (frozenset({"category", "start_year", "end_year"}), frozenset()),
    "average_age_at_award": (frozenset({"category"}), frozenset({"category"})),
    "laureates_by_affiliation_institution": (
        frozenset({"category", "affiliation_country", "limit"}),
        frozenset({"category", "affiliation_country"}),
    ),
}


class NobelStatisticsInput(_ToolInput):
    operation: StatisticOperation = Field(
        description=(
            "One allow-listed aggregate: summary | laureates_by_category | laureates_by_gender | "
            "prizes_by_decade | laureates_by_decade | top_birth_countries | women_by_era | "
            "average_age_at_award | laureates_by_affiliation_institution."
        ),
    )
    category: Category | None = Field(default=None, description="Optional (or required) Nobel category filter.")
    start_year: Year | None = Field(default=None, description="Inclusive first award year.")
    end_year: Year | None = Field(default=None, description="Inclusive last award year.")
    affiliation_country: Country | None = Field(
        default=None,
        description="Country of the award-time INSTITUTION (only for laureates_by_affiliation_institution).",
    )
    limit: Annotated[int, Field(ge=1, le=20), BeforeValidator(_reject_bool)] | None = Field(
        default=None, description="Rows to return for ranked operations (1-20, default 10)."
    )

    @model_validator(mode="after")
    def _check_operation_filters(self) -> "NobelStatisticsInput":
        allowed, required = OPERATION_FILTERS[self.operation]
        supplied = {
            name for name in ("category", "start_year", "end_year", "affiliation_country", "limit")
            if getattr(self, name) is not None
        }
        unsupported = sorted(supplied - allowed)
        if unsupported:
            raise ValueError(f"operation '{self.operation}' does not support: {', '.join(unsupported)}")
        missing = sorted(required - supplied)
        if missing:
            raise ValueError(f"operation '{self.operation}' requires: {', '.join(missing)}")
        if self.start_year and self.end_year and self.start_year > self.end_year:
            raise ValueError("start_year must be less than or equal to end_year")
        return self


# --------------------------------------------------------------------------
# search_nobel_knowledge
# --------------------------------------------------------------------------

class KnowledgeSearchInput(_ToolInput):
    query: str = Field(min_length=1, max_length=500, description="Natural-language question or topic.")
    level: Level | None = Field(
        default=None,
        description="Restrict to educational explanations at this level (Simple, Explore, Advanced, Expert).",
    )
    laureate_id: PositiveId | None = Field(
        default=None, description="Restrict to content credited to this internal laureate_id.",
    )
    k: Annotated[int, Field(ge=1, le=10), BeforeValidator(_reject_bool)] = Field(
        default=5, description="Number of results (1-10)."
    )
    dedupe_by_document: bool = Field(
        default=True,
        description="Return at most one chunk per source document (recommended).",
    )
