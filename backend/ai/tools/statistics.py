"""Allow-listed Nobel statistics built on the existing analytics layer.

Only the operations in ``OPERATIONS`` can run. Each one maps to an existing
analytics service/repository function (parameterised ORM aggregates), and
each result carries its metric definition, counting unit and applied filters
so that different kinds of counts are never confused:

* distinct laureates   - one per person/organization (``Laureate`` rows)
* prizes               - one per (year, category) prize (``Prize`` rows)
* awards               - one per laureate-prize pair (``LaureatePrize`` rows)
* age observations     - one per award with a known birth date
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from backend.ai.tools.schemas import NobelStatisticsInput
from backend.models.category import Category
from backend.models.laureate import Laureate
from backend.models.laureate_prize import LaureatePrize
from backend.models.prize import Prize
from backend.repositories import analytics_repository
from backend.services import analytics_service

DEFAULT_LIMIT = 10

DEFINITIONS: dict[str, dict[str, str]] = {
    "summary": {
        "metric_definition": (
            "Totals for the filtered awards: distinct laureates (persons + organizations), distinct prizes "
            "(one per year and category), laureate-prize awards, distinct birth countries of persons, and "
            "women among persons with a recorded gender."
        ),
        "counting_unit": "mixed; see each value's name",
    },
    "laureates_by_category": {
        "metric_definition": "Distinct laureates per category. A laureate who won in two categories counts in both.",
        "counting_unit": "distinct laureates (persons and organizations)",
    },
    "laureates_by_gender": {
        "metric_definition": "Distinct person laureates per recorded gender. Organizations are excluded.",
        "counting_unit": "distinct person laureates",
    },
    "prizes_by_decade": {
        "metric_definition": "Prizes per award decade; a shared prize counts once.",
        "counting_unit": "prizes (year + category)",
    },
    "laureates_by_decade": {
        "metric_definition": "Distinct laureates with at least one award in each decade.",
        "counting_unit": "distinct laureates (persons and organizations)",
    },
    "top_birth_countries": {
        "metric_definition": (
            "Distinct person laureates per BIRTH country as recorded by the Nobel Prize API. "
            "Organizations and unknown birth countries are excluded. Ties are ordered alphabetically."
        ),
        "counting_unit": "distinct person laureates",
    },
    "women_by_era": {
        "metric_definition": (
            "Women as a percentage of distinct person laureates with a recorded gender, per era "
            "(1901-1950, 1951-1970, 1971-1990, 1991-2010, 2011-present)."
        ),
        "counting_unit": "distinct person laureates per era",
    },
    "average_age_at_award": {
        "metric_definition": (
            "Mean approximate age at award (award year minus birth year) for persons with a known birth date. "
            "A repeat winner contributes one observation per award."
        ),
        "counting_unit": "age-at-award observations",
    },
    "laureates_by_affiliation_institution": {
        "metric_definition": (
            "Distinct laureates per award-time institution located in the given AFFILIATION country "
            "(the institution's country, not the laureate's birth country). Ties are ordered alphabetically."
        ),
        "counting_unit": "distinct laureates",
    },
}

OPERATIONS = tuple(DEFINITIONS)


def _award_counts(db: Session, category: str | None, start: int | None, end: int | None) -> dict[str, int]:
    conditions = []
    if category is not None:
        conditions.append(Category.name == category)
    if start is not None:
        conditions.append(Prize.year >= start)
    if end is not None:
        conditions.append(Prize.year <= end)
    statement = (
        select(
            func.count(LaureatePrize.laureate_prize_id),
            func.count(func.distinct(case((Laureate.laureate_type == "Person", Laureate.laureate_id)))),
            func.count(func.distinct(case((Laureate.laureate_type == "Organization", Laureate.laureate_id)))),
        )
        .select_from(LaureatePrize)
        .join(Laureate, Laureate.laureate_id == LaureatePrize.laureate_id)
        .join(Prize, Prize.prize_id == LaureatePrize.prize_id)
        .join(Category, Category.category_id == Prize.category_id)
    )
    if conditions:
        statement = statement.where(*conditions)
    awards, persons, organizations = db.execute(statement).one()
    return {
        "laureate_prize_awards": int(awards or 0),
        "distinct_person_laureates": int(persons or 0),
        "distinct_organization_laureates": int(organizations or 0),
    }


def _ranked(rows: list[tuple[str, int]], limit: int) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: (-int(row[1]), str(row[0])))
    return [{"name": name, "laureate_count": int(count)} for name, count in ordered[:limit]]


def get_nobel_statistics(params: NobelStatisticsInput, db: Session) -> dict[str, Any]:
    op = params.operation
    category, start, end = params.category, params.start_year, params.end_year
    limit = params.limit or DEFAULT_LIMIT
    extra: dict[str, Any] = {}

    if op == "summary":
        summary = analytics_service.get_summary(db, category, start, end).model_dump()
        rows: Any = {
            "distinct_laureates": summary["total_laureates"],
            **_award_counts(db, category, start, end),
            "prizes": summary["total_prizes"],
            "distinct_birth_countries_of_persons": summary["total_countries"],
            "women_person_laureates": summary["women_laureates"],
            "women_percentage_of_known_gender_persons": summary["women_percentage"],
        }
    elif op == "laureates_by_category":
        rows = [r.model_dump() for r in analytics_service.get_category_counts(db, start, end)]
        rows.sort(key=lambda r: (-r["laureate_count"], r["category"]))
    elif op == "laureates_by_gender":
        counts = analytics_repository.get_overall_gender_counts(db, category, start, end)
        rows = [{"gender": g, "laureate_count": int(n)} for g, n in sorted(counts)]
    elif op == "prizes_by_decade":
        rows = [r.model_dump() for r in analytics_service.get_prize_counts_by_decade(db, category, start, end)]
    elif op == "laureates_by_decade":
        rows = [r.model_dump() for r in analytics_service.get_decade_counts(db, category, start, end)]
    elif op == "top_birth_countries":
        # Fetch every country, then order deterministically before slicing:
        # the repository's LIMIT alone would make ties at the cut-off arbitrary.
        all_rows = analytics_repository.get_top_birth_countries(db, 10_000, category, start, end)
        rows = [{"birth_country": r["name"], "laureate_count": r["laureate_count"]} for r in _ranked(all_rows, limit)]
        extra["countries_with_laureates"] = len(all_rows)
    elif op == "women_by_era":
        rows = [r.model_dump() for r in analytics_service.get_women_percentage_by_era(db, category, start, end)]
    elif op == "average_age_at_award":
        value = analytics_service.get_average_age(db, category).average_age
        rows = {"average_age_at_award": round(value, 1) if value is not None else None}
    elif op == "laureates_by_affiliation_institution":
        all_rows = analytics_repository.get_institution_counts_by_category(db, category, params.affiliation_country)
        rows = [{"institution": r["name"], "laureate_count": r["laureate_count"]} for r in _ranked(all_rows, limit)]
        extra["institutions_with_laureates"] = len(all_rows)
    else:  # pragma: no cover - the input schema only admits allow-listed operations
        raise ValueError(f"unsupported operation {op}")

    return {
        "operation": op,
        **DEFINITIONS[op],
        "applied_filters": params.model_dump(exclude_none=True, exclude={"operation"}),
        "result": rows,
        **extra,
        "empty": rows == [] or (isinstance(rows, dict) and all(v in (None, 0) for v in rows.values())),
        "source": "Nobel Explorer database (Nobel Prize API data imported by ETL)",
    }
