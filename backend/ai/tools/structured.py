"""Structured (exact) retrieval: laureate search and laureate details.

Both functions take a validated input model and a read-only SQLAlchemy
session, reuse the existing service layer (parameterised ORM queries only)
and return plain dictionaries. No SQL text is ever built from user input.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.ai.config import (
    CITATION_SOURCE_LINKED,
    CITATION_STRUCTURED_RECORD,
    CITATION_UNVERIFIED_EDUCATIONAL,
    EDUCATIONAL_LEVELS,
)
from backend.ai.documents import NOBEL_API_SOURCE_NAME, _source_name_for
from backend.ai.tools.schemas import LaureateDetailsInput, SearchLaureatesInput
from backend.models.category import Category
from backend.models.prize import Prize
from backend.services import (
    connection_service,
    contribution_service,
    explanation_service,
    laureate_service,
)

MAX_EXPLANATION_CHARS = 4000
MAX_CONNECTION_DESCRIPTION_CHARS = 400

STRUCTURED_PROVENANCE = {
    "source_name": NOBEL_API_SOURCE_NAME,
    "citation_status": CITATION_STRUCTURED_RECORD,
    "note": "Structured fields imported from the Nobel Prize API; no per-laureate source URL is stored.",
}
COUNTRY_SEMANTICS = (
    "birth_country is the country of birth as recorded by the Nobel Prize API (historical names such as "
    "'Russian Empire' are kept). affiliation_country is the country of the institution the laureate was "
    "affiliated with when the prize was awarded."
)


def _coverage(db: Session, category: str | None = None) -> dict[str, Any]:
    first, last = db.execute(select(func.min(Prize.year), func.max(Prize.year))).one()
    coverage: dict[str, Any] = {"first_prize_year": first, "last_prize_year": last}
    if category is not None:
        cat_first, cat_last = db.execute(
            select(func.min(Prize.year), func.max(Prize.year))
            .join(Category, Category.category_id == Prize.category_id)
            .where(Category.name == category)
        ).one()
        coverage.update(category=category, category_first_year=cat_first, category_last_year=cat_last)
    return coverage


def _award_dict(award) -> dict[str, Any]:
    return {
        "laureate_prize_id": award.laureate_prize_id,
        "prize_id": award.prize.prize_id,
        "year": award.prize.year,
        "category": award.prize.category.name,
        "prize_share": award.prize_share,
        "motivation": award.motivation,
        "affiliations": [
            {
                "institution": inst.name,
                "city": inst.city,
                "state": inst.state,
                "affiliation_country": inst.country,
            }
            for inst in sorted(award.affiliations, key=lambda i: i.institution_id)
        ],
    }


def _laureate_core(detail) -> dict[str, Any]:
    return {
        "laureate_id": detail.laureate_id,
        "nobel_laureate_id": detail.nobel_laureate_id,
        "full_name": detail.full_name,
        "laureate_type": detail.laureate_type,
        "gender": detail.gender,
        "birth_date": detail.birth_date.isoformat() if detail.birth_date else None,
        "birth_city": detail.birth_city,
        "birth_state": detail.birth_state,
        "birth_country": detail.birth_country,
    }


def _matches(award: dict[str, Any], params: SearchLaureatesInput) -> bool:
    return (params.year is None or award["year"] == params.year) and (
        params.category is None or award["category"] == params.category
    )


def search_laureates(params: SearchLaureatesInput, db: Session) -> dict[str, Any]:
    page = laureate_service.list_laureates(
        db,
        params.limit,
        0,
        category=params.category,
        year=params.year,
        country=params.birth_country,
        gender=params.gender,
        search=params.name,
    )
    laureates = []
    for item in page.items:  # repository orders by laureate_id -> deterministic
        detail = laureate_service.get_laureate(db, item.laureate_id)
        awards = [_award_dict(a) for a in detail.awards]
        laureates.append({
            **_laureate_core(detail),
            "matched_awards": [a for a in awards if _matches(a, params)],
            "other_awards": [a for a in awards if not _matches(a, params)],
        })

    applied = params.model_dump(exclude_none=True)
    result: dict[str, Any] = {
        "filters": applied,
        "total_matches": page.total,
        "returned": len(laureates),
        "truncated": page.total > len(laureates),
        "ordering": "laureate_id ascending",
        "ambiguous_name": bool(params.name) and page.total > 1,
        "laureates": laureates,
        "provenance": STRUCTURED_PROVENANCE,
        "country_semantics": COUNTRY_SEMANTICS,
        "message": None,
    }
    if page.total == 0:
        coverage = _coverage(db, params.category)
        hints = [f"The database covers prizes awarded {coverage['first_prize_year']}-{coverage['last_prize_year']}."]
        if params.category and coverage.get("category_first_year"):
            hints.append(
                f"{params.category} prizes in the database run from {coverage['category_first_year']} "
                f"to {coverage['category_last_year']}."
            )
        if params.birth_country:
            hints.append("birth_country must match the stored country name (e.g. 'USA', 'United Kingdom').")
        if params.name:
            hints.append("name is a substring match on the full stored name.")
        result["message"] = "No laureates matched these filters. " + " ".join(hints)
        result["coverage"] = coverage
    elif result["ambiguous_name"]:
        result["message"] = (
            f"{page.total} laureates match the name '{params.name}'. "
            "Choose a laureate_id before requesting details."
        )
    elif result["truncated"]:
        result["message"] = f"Showing {len(laureates)} of {page.total} matches; narrow the filters or raise limit."
    return result


def _source(url: str | None, name: str | None = None) -> dict[str, str] | None:
    if not url:
        return None
    return {"name": name or _source_name_for(url), "url": url}


def get_laureate_details(params: LaureateDetailsInput, db: Session) -> dict[str, Any]:
    detail = laureate_service.get_laureate(db, params.laureate_id)  # ResourceNotFoundError if missing
    contributions = []
    for contribution in contribution_service.list_laureate_contributions(db, params.laureate_id):
        cid = contribution.contribution_id
        explanations = explanation_service.list_explanations(db, cid)
        levels = sorted(
            (e.level for e in explanations),
            key=lambda level: EDUCATIONAL_LEVELS.index(level) if level in EDUCATIONAL_LEVELS else len(EDUCATIONAL_LEVELS),
        )
        contribution_source = _source(contribution.source_url)
        item: dict[str, Any] = {
            "contribution_id": cid,
            "title": contribution.title,
            "contribution_type": contribution.contribution_type,
            "summary": contribution.summary,
            "significance": contribution.significance,
            "source": contribution_source,
            "citation_status": CITATION_SOURCE_LINKED if contribution_source else CITATION_UNVERIFIED_EDUCATIONAL,
            "explanation_levels_available": levels,
            "connections": [],
        }
        if params.include_explanation_level:
            match = next((e for e in explanations if e.level == params.include_explanation_level), None)
            if match is None:
                item["explanation"] = None
                item["explanation_message"] = (
                    f"No {params.include_explanation_level} explanation is stored for this contribution."
                )
            else:
                text = match.explanation_text
                item["explanation"] = {
                    "level": match.level,
                    "text": text[:MAX_EXPLANATION_CHARS],
                    "truncated": len(text) > MAX_EXPLANATION_CHARS,
                    "key_concepts": [c.strip() for c in (match.key_concepts or "").splitlines() if c.strip()],
                    "citation_status": CITATION_UNVERIFIED_EDUCATIONAL,
                    "related_source": contribution_source,
                    "note": "Educational explanation without a stored citation; related_source is context only.",
                }
        for connection in connection_service.list_connections(db, cid):
            description = connection.description or ""
            connection_source = _source(connection.source_url, connection.source_name)
            item["connections"].append({
                "connection_id": connection.connection_id,
                "connection_type": connection.connection_type,
                "title": connection.title,
                "description": description[:MAX_CONNECTION_DESCRIPTION_CHARS],
                "description_truncated": len(description) > MAX_CONNECTION_DESCRIPTION_CHARS,
                "source": connection_source,
                "citation_status": CITATION_SOURCE_LINKED if connection_source else CITATION_UNVERIFIED_EDUCATIONAL,
                "related_prize": (
                    {"year": connection.related_prize.year, "category": connection.related_prize.category}
                    if connection.related_prize else None
                ),
            })
        contributions.append(item)

    return {
        "laureate": _laureate_core(detail),
        "awards": [_award_dict(a) for a in detail.awards],
        "contributions": contributions,
        "educational_content_available": bool(contributions),
        "message": None if contributions else (
            "No educational contributions or explanations are stored for this laureate; "
            "only structured prize data is available."
        ),
        "provenance": STRUCTURED_PROVENANCE,
        "country_semantics": COUNTRY_SEMANTICS,
    }
