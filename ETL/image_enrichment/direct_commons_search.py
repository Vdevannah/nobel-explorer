from __future__ import annotations

from typing import Any

from ETL.image_enrichment.commons import CommonsClient
from ETL.image_enrichment.enrichment import enrich_commons_for_identity
from ETL.image_enrichment.wikipedia_fallback import (
    is_plausible_portrait_filename,
    candidate_search_queries,
)

# Phase 7.5J step 4: organizations legitimately have logos/emblems/
# buildings as their representative image -- the people-oriented
# blocklist would wrongly reject those, so organization search allows
# them through (still excluding flags/maps/unrelated decorative content).
_ORG_ALLOWED_DESPITE_BLOCKLIST = ("logo", "emblem", "seal of", "headquarters", "building")


def search_person_candidates(
    commons_client: CommonsClient,
    full_name: str,
    limit_per_query: int = 6,
) -> list[str]:
    """Direct Commons File-namespace search for a person, independent of
    Wikidata P18 / Wikipedia PageImages. Returns plausible-portrait
    filenames only (blocklist-filtered); never identity-verified here --
    callers must still validate license and confirm identity/suitability.
    """
    seen: list[str] = []
    seen_set: set[str] = set()
    for query in candidate_search_queries(full_name):
        for filename in commons_client.search_files(query, limit=limit_per_query):
            if filename in seen_set:
                continue
            seen_set.add(filename)
            if is_plausible_portrait_filename(filename):
                seen.append(filename)
        if seen:
            break
    return seen


def search_organization_candidates(
    commons_client: CommonsClient,
    full_name: str,
    limit_per_query: int = 6,
) -> list[str]:
    """Direct Commons search for an organization visual (logo, emblem,
    building, historical photo) -- Phase 7.5J step 4. Logos/buildings are
    acceptable here, unlike the person search path.
    """
    seen: list[str] = []
    seen_set: set[str] = set()
    for query in (full_name, f"{full_name} logo"):
        for filename in commons_client.search_files(query, limit=limit_per_query):
            if filename in seen_set:
                continue
            seen_set.add(filename)
            lowered = filename.lower()
            if is_plausible_portrait_filename(filename) or any(
                marker in lowered for marker in _ORG_ALLOWED_DESPITE_BLOCKLIST
            ):
                seen.append(filename)
        if seen:
            break
    return seen


def validate_candidate(
    commons_client: CommonsClient,
    laureate_id: int | None,
    nobel_laureate_id: str,
    full_name: str,
    candidate_filename: str,
) -> dict[str, Any]:
    """Run the SAME Commons license/provenance validation used everywhere
    else in this pipeline (enrich_commons_for_identity, unchanged) against
    a direct-search candidate. Never a second, weaker validator.
    """
    fake_identity = {
        "proposed_action": "ACCEPT",
        "p18_filename": candidate_filename,
        "laureate_id": laureate_id,
        "nobel_laureate_id": nobel_laureate_id,
        "full_name": full_name,
    }
    return enrich_commons_for_identity(fake_identity, commons_client)
