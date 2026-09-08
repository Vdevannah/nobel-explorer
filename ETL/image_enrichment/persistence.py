from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.orm import Session

from backend.models.laureate import Laureate
from backend.repositories import laureate_repository


TRACKING_PARAM_PREFIXES = ("utm_",)


def strip_tracking_params(url: str | None) -> str | None:
    """Remove marketing/tracking query parameters (utm_*) from a URL.

    Preserves scheme, host, path, fragment, and any non-tracking query
    parameters exactly. Returns the URL unchanged if it has no query
    string, and returns None/"" unchanged for falsy input.
    """
    if not url:
        return url
    parts = urlsplit(url)
    if not parts.query:
        return url

    kept_params = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith(TRACKING_PARAM_PREFIXES)
    ]
    new_query = urlencode(kept_params)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, new_query, parts.fragment)
    )


def _dedupe_exact_repeat(segment: str) -> str:
    """Collapse a segment that consists of the exact same phrase repeated
    twice back-to-back (e.g. "Unknown author Unknown author" ->
    "Unknown author"). Only fires on an exact, whole-phrase duplicate;
    never touches text that merely repeats a single word.
    """
    words = segment.split()
    count = len(words)
    if count >= 2 and count % 2 == 0:
        half = count // 2
        if words[:half] == words[half:]:
            return " ".join(words[:half])
    return segment


def cleanup_attribution(attribution: str | None) -> str | None:
    """Conservative final cleanup pass over Phase 7.5D's normalized
    attribution: collapses an exact repeated adjacent phrase before any
    parenthetical credit/source note. Never invents a name; if nothing
    is safely dedupe-able, the original normalized text is preserved
    unchanged.
    """
    if not attribution:
        return attribution

    if "(" in attribution:
        prefix, _, rest = attribution.partition("(")
        cleaned_prefix = _dedupe_exact_repeat(prefix.strip())
        if not cleaned_prefix:
            return f"({rest}"
        return f"{cleaned_prefix} ({rest}"

    return _dedupe_exact_repeat(attribution.strip())


def build_persistence_payload(
    commons_result: dict[str, Any]
) -> dict[str, Any] | None:
    """Build the four-field persistence payload from an already-validated
    Phase 7.5D result.

    Returns None when the record is not approved for persistence (the
    identity decision or the Commons decision was not ACCEPT), or when
    the validated metadata is unexpectedly incomplete. Never re-derives
    or rediscovers image data independently.
    """
    if commons_result.get("identity_decision") != "ACCEPT":
        return None
    if commons_result.get("commons_decision") != "ACCEPT":
        return None

    image_url = strip_tracking_params(commons_result.get("image_url_candidate"))
    source_url = strip_tracking_params(commons_result.get("canonical_source_url"))
    attribution = cleanup_attribution(commons_result.get("attribution_normalized"))
    license_value = commons_result.get("license_normalized")

    if not image_url or not source_url or not license_value:
        return None

    return {
        "image_url": image_url,
        "image_source_url": source_url,
        "image_attribution": attribution,
        "image_license": license_value,
    }


def has_existing_image_metadata(laureate: Laureate) -> bool:
    """Conservative existing-image check: any populated image_url means
    "already has an image" for missing-only purposes, regardless of
    whether the other three fields are also populated.
    """
    return bool(laureate.image_url)


def plan_persistence(
    db: Session,
    commons_results: list[dict[str, Any]],
    force: bool = False,
) -> list[dict[str, Any]]:
    """Compute, for every Commons-validated result, exactly what
    persistence action would be taken. Performs no writes; safe to call
    in both dry-run and persist modes.
    """
    plans: list[dict[str, Any]] = []

    for result in commons_results:
        nobel_id = result.get("nobel_laureate_id")
        base = {"nobel_laureate_id": nobel_id, "full_name": result.get("full_name")}

        identity_action = result.get("identity_decision")
        commons_action = result.get("commons_decision")

        if identity_action != "ACCEPT" or commons_action != "ACCEPT":
            category = "skip" if "SKIP" in (identity_action, commons_action) else "review"
            plans.append({
                **base,
                "action": category,
                "reason": (
                    f"identity_decision={identity_action!r}, "
                    f"commons_decision={commons_action!r}"
                ),
            })
            continue

        laureate = laureate_repository.get_by_nobel_id(db, nobel_id)
        if laureate is None:
            plans.append({
                **base,
                "action": "failed",
                "reason": "laureate not found in database",
            })
            continue

        payload = build_persistence_payload(result)
        if payload is None:
            plans.append({
                **base,
                "action": "failed",
                "reason": "approved but validated payload was incomplete",
            })
            continue

        existing = has_existing_image_metadata(laureate)
        if existing and not force:
            plans.append({
                **base,
                "action": "skipped_existing",
                "reason": "image_url already populated (missing-only mode)",
                "existing_image_url": laureate.image_url,
            })
            continue

        plans.append({
            **base,
            "action": "update",
            "payload": payload,
            "force_applied": bool(existing and force),
        })

    return plans


def apply_persistence(
    db: Session,
    plans: list[dict[str, Any]],
) -> dict[str, Any]:
    """Apply every 'update' plan in a single all-or-nothing transaction.

    Rolls back the entire batch on any failure so a persistence run never
    leaves a partial, silently-half-applied state.
    """
    updates = [plan for plan in plans if plan["action"] == "update"]
    applied_ids: list[str] = []

    try:
        for plan in updates:
            laureate = laureate_repository.get_by_nobel_id(
                db, plan["nobel_laureate_id"]
            )
            if laureate is None:
                raise RuntimeError(
                    f"laureate {plan['nobel_laureate_id']} vanished during persistence"
                )
            payload = plan["payload"]
            laureate_repository.update_image_metadata(
                db,
                laureate,
                image_url=payload["image_url"],
                image_source_url=payload["image_source_url"],
                image_attribution=payload["image_attribution"],
                image_license=payload["image_license"],
            )
            applied_ids.append(plan["nobel_laureate_id"])
        db.commit()
    except Exception as error:  # noqa: BLE001 - report, never swallow silently
        db.rollback()
        return {"committed": False, "updated_ids": [], "error": str(error)}

    return {"committed": True, "updated_ids": applied_ids, "error": None}


def run_persistence(
    db: Session,
    commons_results: list[dict[str, Any]],
    mode: str = "dry-run",
    force: bool = False,
) -> dict[str, Any]:
    """Plan, and optionally apply, image-metadata persistence for a batch
    of already Phase-7.5D-validated results.

    mode="dry-run" (the default) performs zero database writes and only
    reports what would happen. mode="persist" applies approved,
    missing-only (unless force=True) updates in one transaction.
    """
    if mode not in ("dry-run", "persist"):
        raise ValueError(f"unknown persistence mode: {mode!r}")

    plans = plan_persistence(db, commons_results, force=force)

    summary: dict[str, Any] = {
        "mode": mode,
        "force": force,
        "updated": 0,
        "skipped_existing": 0,
        "review": 0,
        "skip": 0,
        "failed": 0,
        "database_writes": 0,
        "records": plans,
    }

    for plan in plans:
        if plan["action"] in ("skipped_existing", "review", "skip", "failed"):
            summary[plan["action"]] += 1

    if mode == "dry-run":
        summary["updated"] = sum(1 for plan in plans if plan["action"] == "update")
        return summary

    result = apply_persistence(db, plans)
    if not result["committed"]:
        summary["failed"] += sum(1 for plan in plans if plan["action"] == "update")
        summary["error"] = result["error"]
        return summary

    summary["updated"] = len(result["updated_ids"])
    summary["database_writes"] = len(result["updated_ids"])
    return summary


def load_commons_report(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("results", [])
