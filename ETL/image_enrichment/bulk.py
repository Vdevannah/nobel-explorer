from __future__ import annotations

from typing import Any, Callable, Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.laureate import Laureate
from ETL.image_enrichment.commons import CommonsClient
from ETL.image_enrichment.enrichment import (
    enrich_commons_for_identity,
    enrich_laureate_dry_run,
)
from ETL.image_enrichment.persistence import apply_persistence, plan_persistence
from ETL.image_enrichment.sources import WikidataClient


DEFAULT_BATCH_SIZE = 50
SYSTEMIC_FAILURE_RATIO = 0.5

ProgressCallback = Callable[[int, dict[str, int], str | None], None]
RecordCallback = Callable[[int, str, dict[str, Any]], None]


def select_missing_image_nobel_ids(
    db: Session,
    limit: int | None = None,
    offset: int = 0,
    force: bool = False,
) -> list[str]:
    """Select nobel_laureate_ids in deterministic laureate_id order.

    Missing-only by default (image_url IS NULL). force=True considers
    every laureate in range regardless of existing image metadata.
    """
    statement = select(Laureate.nobel_laureate_id).order_by(Laureate.laureate_id)
    if not force:
        statement = statement.where(Laureate.image_url.is_(None))
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement).all())


def chunked(items: list[str], size: int) -> Iterator[list[str]]:
    for start in range(0, len(items), size):
        yield items[start:start + size]


def classify_result(result: dict[str, Any]) -> str:
    """Bucket a Commons-validated result for aggregate reporting.

    One of: identity_review, identity_skip, network_failed, no_image,
    commons_accept, commons_review, commons_skip.
    """
    identity = result.get("identity_decision")
    if identity == "REVIEW":
        return "identity_review"
    if identity != "ACCEPT":
        return "identity_skip"
    if result.get("commons_lookup_status") == "error":
        return "network_failed"
    if not result.get("p18_filename"):
        return "no_image"
    commons = result.get("commons_decision")
    if commons == "ACCEPT":
        return "commons_accept"
    if commons == "REVIEW":
        return "commons_review"
    return "commons_skip"


def _empty_counts() -> dict[str, int]:
    return {
        "total_considered": 0,
        "total_processed": 0,
        "identity_accept": 0,
        "identity_review": 0,
        "identity_skip": 0,
        "commons_accept": 0,
        "commons_review": 0,
        "commons_skip": 0,
        "no_image": 0,
        "network_failed": 0,
        "database_failed": 0,
        "persisted": 0,
        "skipped_existing": 0,
    }


def _compact_entry(result: dict[str, Any], bucket: str) -> dict[str, Any]:
    return {
        "nobel_laureate_id": result.get("nobel_laureate_id"),
        "laureate_id": result.get("laureate_id"),
        "full_name": result.get("full_name"),
        "candidate_wikidata_id": result.get("wikidata_entity_id"),
        "confidence": result.get("identity_confidence"),
        "identity_decision": result.get("identity_decision"),
        "commons_decision": result.get("commons_decision"),
        "copyright_decision": result.get("copyright_decision"),
        "non_copyright_restrictions": result.get("non_copyright_restrictions", []),
        "p18_filename": result.get("p18_filename"),
        "bucket": bucket,
        "reason": (
            "; ".join(result.get("skip_reasons", []) + result.get("review_reasons", []))
            or result.get("lookup_error")
            or None
        ),
        "warnings": result.get("warnings", []),
    }


def run_bulk_enrichment(
    db: Session,
    nobel_ids: list[str],
    mode: str = "dry-run",
    force: bool = False,
    batch_size: int = DEFAULT_BATCH_SIZE,
    wikidata_client: WikidataClient | None = None,
    commons_client: CommonsClient | None = None,
    progress_callback: ProgressCallback | None = None,
    record_callback: RecordCallback | None = None,
) -> dict[str, Any]:
    """Run the Phase 7.5C/D/E pipeline over a batch of laureates in
    internal chunks, aggregating counts and (in "persist" mode) writing
    ACCEPT+ACCEPT records only, chunk-by-chunk with per-chunk transaction
    safety.

    Stops early ("stopped_early": True) on a systemic network failure
    (a majority of a chunk failing to reach Commons/Wikidata) or a
    database failure while persisting a chunk, rather than continuing
    blindly. Reuses Phase 7.5C/D/E functions unchanged; this module only
    adds selection, chunking, and aggregation.
    """
    if mode not in ("dry-run", "persist"):
        raise ValueError(f"unknown mode: {mode!r}")

    wikidata = wikidata_client or WikidataClient()
    commons = commons_client or CommonsClient()

    counts = _empty_counts()
    counts["total_considered"] = len(nobel_ids)
    records: list[dict[str, Any]] = []
    review_queue: list[dict[str, Any]] = []
    chunk_summaries: list[dict[str, Any]] = []
    stopped_early = False
    stop_reason: str | None = None

    for chunk_index, chunk_ids in enumerate(chunked(nobel_ids, batch_size)):
        results = []
        for nobel_id in chunk_ids:
            identity = enrich_laureate_dry_run(db, nobel_id, wikidata)
            result = enrich_commons_for_identity(identity, commons)
            results.append(result)
            if record_callback:
                record_callback(chunk_index, nobel_id, result)
        counts["total_processed"] += len(results)

        network_failures = 0
        for result in results:
            bucket = classify_result(result)
            identity = result.get("identity_decision")
            if identity == "ACCEPT":
                counts["identity_accept"] += 1
            elif identity == "REVIEW":
                counts["identity_review"] += 1
            else:
                counts["identity_skip"] += 1

            if bucket == "network_failed":
                network_failures += 1
                counts["network_failed"] += 1
            elif bucket in (
                "no_image", "commons_accept", "commons_review", "commons_skip"
            ):
                counts[bucket] += 1
            # bucket in ("identity_review", "identity_skip") is already
            # accounted for by the identity_decision branch above.

            if bucket != "commons_accept":
                records.append(_compact_entry(result, bucket))
            if bucket in ("identity_review", "commons_review"):
                review_queue.append(_compact_entry(result, bucket))

        if results and (network_failures / len(results)) >= SYSTEMIC_FAILURE_RATIO:
            stopped_early = True
            stop_reason = (
                f"systemic network failure in chunk {chunk_index} "
                f"({network_failures}/{len(results)} records failed)"
            )
            chunk_summaries.append({
                "chunk_index": chunk_index,
                "size": len(chunk_ids),
                "stopped": True,
                "reason": stop_reason,
            })
            if progress_callback:
                progress_callback(chunk_index, counts, stop_reason)
            break

        chunk_summary: dict[str, Any] = {
            "chunk_index": chunk_index,
            "size": len(chunk_ids),
        }

        if mode == "persist":
            plans = plan_persistence(db, results, force=force)
            apply_result = apply_persistence(db, plans)
            if not apply_result["committed"]:
                planned_updates = sum(1 for plan in plans if plan["action"] == "update")
                counts["database_failed"] += planned_updates
                stopped_early = True
                stop_reason = (
                    f"database failure while persisting chunk {chunk_index}: "
                    f"{apply_result['error']}"
                )
                chunk_summary["stopped"] = True
                chunk_summary["reason"] = stop_reason
                chunk_summaries.append(chunk_summary)
                if progress_callback:
                    progress_callback(chunk_index, counts, stop_reason)
                break

            counts["persisted"] += len(apply_result["updated_ids"])
            counts["skipped_existing"] += sum(
                1 for plan in plans if plan["action"] == "skipped_existing"
            )
            chunk_summary["persisted"] = len(apply_result["updated_ids"])
            chunk_summary["skipped_existing"] = sum(
                1 for plan in plans if plan["action"] == "skipped_existing"
            )
        else:
            plans = plan_persistence(db, results, force=force)
            chunk_summary["would_persist"] = sum(
                1 for plan in plans if plan["action"] == "update"
            )
            chunk_summary["skipped_existing"] = sum(
                1 for plan in plans if plan["action"] == "skipped_existing"
            )

        chunk_summaries.append(chunk_summary)
        if progress_callback:
            progress_callback(chunk_index, counts, None)

    return {
        "mode": mode,
        "force": force,
        "batch_size": batch_size,
        "stopped_early": stopped_early,
        "stop_reason": stop_reason,
        "counts": counts,
        "chunks": chunk_summaries,
        "records": records,
        "review_queue": review_queue,
    }
