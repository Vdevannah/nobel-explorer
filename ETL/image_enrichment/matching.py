from __future__ import annotations

import re
import unicodedata
from typing import Any

from ETL.image_enrichment.validation import (
    HUMAN_QID,
    validate_organization_candidate,
    validate_person_candidate,
)


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(character for character in value if not unicodedata.combining(character))
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _tokens_without_initials(value: str) -> list[str]:
    return [token for token in normalize_name(value).split() if len(token) > 1]


def compare_names(source_name: str, candidate_names: list[str]) -> tuple[int, str | None]:
    source = normalize_name(source_name)
    source_tokens = _tokens_without_initials(source_name)

    for candidate_name in candidate_names:
        if source == normalize_name(candidate_name):
            return 3, "exact normalized name or alias matched"

    for candidate_name in candidate_names:
        candidate = normalize_name(candidate_name)
        candidate_tokens = _tokens_without_initials(candidate_name)
        if (
            source_tokens
            and candidate_tokens
            and (
                set(source_tokens).issubset(candidate_tokens)
                or set(candidate_tokens).issubset(source_tokens)
            )
        ):
            return 2, "name variation or initials relationship matched"
        if source in candidate or candidate in source:
            return 1, "partial name matched"
    return 0, None


def _contains_nobel_evidence(candidate: dict[str, Any]) -> bool:
    return any(
        "nobel" in normalize_name(label)
        for label in candidate.get("award_labels", [])
    )


def evaluate_candidate(
    laureate: dict[str, Any],
    candidate: dict[str, Any]
) -> dict[str, Any]:
    is_person = laureate["laureate_type"] == "Person"
    conflicts = (
        validate_person_candidate(laureate, candidate)
        if is_person
        else validate_organization_candidate(laureate, candidate)
    )
    reasons = []
    score = 0
    candidate_names = [candidate.get("label") or ""] + candidate.get(
        "aliases",
        []
    )
    name_score, name_reason = compare_names(
        laureate["full_name"],
        candidate_names
    )
    score += name_score
    if name_reason:
        reasons.append(name_reason)

    if is_person and HUMAN_QID in candidate.get("instance_of_ids", []):
        score += 2
        reasons.append("candidate is human")
    elif not is_person and HUMAN_QID not in candidate.get("instance_of_ids", []):
        score += 2
        reasons.append("candidate is a non-human entity")

    source_birth = laureate.get("birth_date")
    candidate_birth = candidate.get("birth_date")
    if is_person and source_birth and candidate_birth and not conflicts:
        source_date = str(source_birth)
        candidate_date = candidate_birth[:10]
        if source_date == candidate_date:
            score += 3
            reasons.append("birth date matched")
        elif source_date[:4] == candidate_date[:4]:
            score += 2
            reasons.append("birth year matched")

    if _contains_nobel_evidence(candidate):
        score += 3
        reasons.append("structured Nobel award evidence found")
    elif "nobel" in normalize_name(candidate.get("description")):
        score += 1
        reasons.append("description contains Nobel context")

    if conflicts:
        confidence = "rejected"
    elif score >= 8 and name_score >= 2:
        confidence = "high"
    elif score >= 5 and name_score >= 1:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "entity_id": candidate.get("entity_id"),
        "label": candidate.get("label"),
        "description": candidate.get("description"),
        "score": score,
        "confidence": confidence,
        "reasons": reasons,
        "conflicts": conflicts,
        "has_p18": candidate.get("has_p18", False),
        "p18_filename": candidate.get("p18_filename"),
    }


def select_candidate(
    laureate: dict[str, Any],
    candidates: list[dict[str, Any]]
) -> dict[str, Any]:
    evaluations = [evaluate_candidate(laureate, candidate) for candidate in candidates]
    viable = sorted(
        (item for item in evaluations if item["confidence"] != "rejected"),
        key=lambda item: item["score"],
        reverse=True
    )

    if not viable:
        confidence = "rejected" if evaluations else "low"
        return {
            "matched": False,
            "confidence": confidence,
            "selected_entity_id": None,
            "reasons": [],
            "conflicts": [
                conflict
                for item in evaluations
                for conflict in item["conflicts"]
            ],
            "proposed_action": "SKIP",
            "has_p18": False,
            "p18_filename": None,
            "candidates_considered": evaluations,
            "review_reason": "no safe candidate found",
        }

    best = viable[0]
    similarly_plausible = [
        item for item in viable[1:]
        if item["score"] >= 5 and best["score"] - item["score"] <= 1
    ]
    if similarly_plausible:
        return {
            "matched": False,
            "confidence": "ambiguous",
            "selected_entity_id": None,
            "reasons": best["reasons"],
            "conflicts": ["multiple candidates are similarly plausible"],
            "proposed_action": "REVIEW",
            "has_p18": False,
            "p18_filename": None,
            "candidates_considered": evaluations,
            "review_reason": "multiple similarly plausible candidates",
        }

    action = "ACCEPT" if best["confidence"] == "high" else "REVIEW"
    return {
        "matched": best["confidence"] in {"high", "medium"},
        "confidence": best["confidence"],
        "selected_entity_id": best["entity_id"],
        "reasons": best["reasons"],
        "conflicts": best["conflicts"],
        "proposed_action": action,
        "has_p18": best["has_p18"],
        "p18_filename": best["p18_filename"],
        "candidates_considered": evaluations,
        "review_reason": (
            None if best["confidence"] == "high"
            else "candidate requires manual review"
        ),
    }
