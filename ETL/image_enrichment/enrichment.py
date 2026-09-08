from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from backend.repositories import laureate_repository
from ETL.image_enrichment.commons import CommonsClient, CommonsError
from ETL.image_enrichment.matching import select_candidate
from ETL.image_enrichment.sources import WikidataClient, WikidataError
from ETL.image_enrichment.validation import (
    decide_commons_validation,
    normalize_attribution,
    normalize_license,
    validate_media_type,
)


def _date_value(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def build_laureate_evidence(laureate: Any) -> dict[str, Any]:
    return {
        "laureate_id": laureate.laureate_id,
        "nobel_laureate_id": laureate.nobel_laureate_id,
        "full_name": laureate.full_name,
        "laureate_type": laureate.laureate_type,
        "birth_date": _date_value(laureate.birth_date),
        "birth_city": laureate.birth_city,
        "birth_state": laureate.birth_state,
        "birth_country": laureate.birth_country,
    }


def enrich_laureate_dry_run(
    db: Session,
    nobel_laureate_id: str,
    client: WikidataClient
) -> dict[str, Any]:
    laureate = laureate_repository.get_by_nobel_id(db, nobel_laureate_id)
    if laureate is None:
        return {
            "nobel_laureate_id": nobel_laureate_id,
            "confidence": "rejected",
            "matched": False,
            "proposed_action": "SKIP",
            "review_reason": "laureate not found in Nobel Explorer",
        }

    evidence = build_laureate_evidence(laureate)
    result: dict[str, Any] = {
        **evidence,
        "database_birth_evidence": {
            "birth_date": evidence["birth_date"],
            "birth_city": evidence["birth_city"],
            "birth_state": evidence["birth_state"],
            "birth_country": evidence["birth_country"],
        },
    }

    try:
        search_results = client.search_wikidata_entities(
            laureate.full_name,
            limit=3
        )
        if not search_results and "," in laureate.full_name:
            search_results = client.search_wikidata_entities(
                laureate.full_name.split(",", 1)[0],
                limit=3,
            )
        candidates = client.get_wikidata_entities([
            item["entity_id"] for item in search_results
        ])
        result.update(select_candidate(evidence, candidates))
    except WikidataError as error:
        result.update({
            "matched": False,
            "confidence": "rejected",
            "selected_entity_id": None,
            "reasons": [],
            "conflicts": [],
            "proposed_action": "SKIP",
            "has_p18": None,
            "p18_filename": None,
            "candidates_considered": [],
            "review_reason": str(error),
        })
    return result


def run_dry_run(
    db: Session,
    nobel_laureate_ids: list[str],
    client: WikidataClient | None = None
) -> dict[str, Any]:
    wikidata_client = client or WikidataClient()
    results = [
        enrich_laureate_dry_run(db, nobel_id, wikidata_client)
        for nobel_id in nobel_laureate_ids
    ]
    return {
        "mode": "dry-run",
        "database_writes": 0,
        "laureate_count": len(results),
        "results": results,
    }


def enrich_commons_for_identity(
    identity: dict[str, Any],
    commons_client: CommonsClient,
) -> dict[str, Any]:
    """Take an already-computed Wikidata identity result (from
    enrich_laureate_dry_run) and, when it was ACCEPTed and carries a P18
    filename, validate the corresponding Commons file's license,
    attribution, and media suitability. Read-only; performs no database
    writes.
    """
    p18_filename = identity.get("p18_filename")
    identity_action = identity.get("proposed_action")

    file_info: dict[str, Any] | None = None
    lookup_status = "skipped"
    lookup_error: str | None = None

    if identity_action == "ACCEPT" and p18_filename:
        try:
            file_info = commons_client.get_file_info(p18_filename)
            lookup_status = "found" if file_info is not None else "missing"
        except CommonsError as error:
            lookup_status = "error"
            lookup_error = str(error)

    license_info = None
    attribution_info = None
    media_info = None
    if file_info is not None:
        extmetadata = file_info.get("extmetadata", {})
        license_info = normalize_license(extmetadata)
        attribution_info = normalize_attribution(extmetadata)
        media_info = validate_media_type(
            file_info.get("mime"),
            has_browser_thumbnail=bool(file_info.get("thumbnail_url")),
        )

    decision = decide_commons_validation(
        identity_action=identity_action,
        p18_filename=p18_filename,
        commons_lookup_status=lookup_status,
        file_info=file_info,
        license_info=license_info,
        attribution_info=attribution_info,
        media_info=media_info,
    )

    result: dict[str, Any] = {
        "laureate_id": identity.get("laureate_id"),
        "nobel_laureate_id": identity.get("nobel_laureate_id"),
        "full_name": identity.get("full_name"),
        "wikidata_entity_id": identity.get("selected_entity_id"),
        "identity_confidence": identity.get("confidence"),
        "p18_filename": p18_filename,
        "identity_decision": identity_action,
        "commons_lookup_status": lookup_status,
        "image_url_candidate": (
            (file_info.get("thumbnail_url") or file_info.get("image_url"))
            if file_info else None
        ),
        "canonical_source_url": (
            file_info.get("canonical_source_url") if file_info else None
        ),
        "width": file_info.get("width") if file_info else None,
        "height": file_info.get("height") if file_info else None,
        "media_type": file_info.get("mime") if file_info else None,
        "license_raw": (
            {
                "license_short_name": license_info["raw_license_short_name"],
                "license": license_info["raw_license"],
                "usage_terms": license_info["raw_usage_terms"],
                "license_url": license_info["license_url"],
            }
            if license_info else None
        ),
        "license_normalized": (
            license_info["normalized"] if license_info else None
        ),
        "attribution_normalized": (
            attribution_info["normalized"] if attribution_info else None
        ),
        "commons_decision": decision["decision"],
        "copyright_decision": decision.get("copyright_decision"),
        "non_copyright_restrictions": decision.get("non_copyright_restrictions", []),
        "reasons": decision["reasons"],
        "review_reasons": decision["review_reasons"],
        "skip_reasons": decision["skip_reasons"],
        "warnings": decision["warnings"],
        "database_write": False,
    }
    if lookup_error:
        result["lookup_error"] = lookup_error
    return result


def run_commons_dry_run(
    db: Session,
    nobel_laureate_ids: list[str],
    wikidata_client: WikidataClient | None = None,
    commons_client: CommonsClient | None = None,
) -> dict[str, Any]:
    """Run the full Wikidata identity + Commons metadata validation
    pipeline for a batch of laureates. Dry-run only: zero database writes.
    """
    wikidata = wikidata_client or WikidataClient()
    commons = commons_client or CommonsClient()

    identities = [
        enrich_laureate_dry_run(db, nobel_id, wikidata)
        for nobel_id in nobel_laureate_ids
    ]
    results = [
        enrich_commons_for_identity(identity, commons)
        for identity in identities
    ]
    return {
        "mode": "dry-run",
        "database_writes": 0,
        "laureate_count": len(results),
        "results": results,
    }
