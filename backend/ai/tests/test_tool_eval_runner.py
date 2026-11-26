"""Tests for the scripted tool-evaluation runner and its dataset."""

import json
from collections import Counter

import pytest

from backend.ai.evaluation.run_tool_eval import DATASET, _check, _resolve_args, resolve
from backend.ai.tools.schemas import (
    KnowledgeSearchInput,
    LaureateDetailsInput,
    NobelStatisticsInput,
    SearchLaureatesInput,
)

SCHEMAS = {
    "search_laureates": SearchLaureatesInput,
    "get_laureate_details": LaureateDetailsInput,
    "get_nobel_statistics": NobelStatisticsInput,
    "search_nobel_knowledge": KnowledgeSearchInput,
}
SAMPLE = {"ok": True, "data": {"laureates": [
    {"full_name": "Carolyn R. Bertozzi", "laureate_id": 356},
    {"full_name": "K. Barry Sharpless", "laureate_id": 766},
]}}


def test_resolve_paths():
    assert resolve(SAMPLE, "data.laureates.*.laureate_id") == [356, 766]
    assert resolve(SAMPLE, "data.laureates.[full_name=Carolyn R. Bertozzi].laureate_id") == 356
    assert resolve(SAMPLE, "data.laureates.1.full_name") == "K. Barry Sharpless"


def test_checks_detect_wrong_answers():
    assert _check(SAMPLE, {"path": "data.laureates.*.laureate_id", "equals": [356, 766]})[0] is True
    assert _check(SAMPLE, {"path": "data.laureates.*.laureate_id", "equals": [356]})[0] is False
    assert _check(SAMPLE, {"path": "data.missing", "equals": 1})[0] is False
    assert _check(SAMPLE, {"path": "data.laureates.*.full_name",
                           "any_in_first": {"k": 1, "values": ["K. Barry Sharpless"]}})[0] is False


def test_argument_references_resolve_and_fail_loudly():
    args = _resolve_args({"laureate_id": {"$ref": 0, "path": "data.laureates.0.laureate_id"}}, [SAMPLE])
    assert args == {"laureate_id": 356}
    with pytest.raises(ValueError):
        _resolve_args({"laureate_id": {"$ref": 0, "path": "data.nothing"}}, [SAMPLE])


def test_dataset_is_well_formed():
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    cases = data["cases"]
    assert len(cases) >= 24
    assert len({c["id"] for c in cases}) == len(cases)
    groups = Counter(c["group"] for c in cases)
    for group in ("exact_structured", "laureate_details", "statistics", "semantic", "multi_step",
                  "ambiguous", "unsupported_category", "out_of_scope", "false_premise"):
        assert groups[group] >= 1, group
    for case in cases:
        for step in case["steps"]:
            assert step["tool"] in SCHEMAS and step["expect"]


def test_dataset_literal_arguments_match_tool_schemas():
    """Arguments expected to be valid must validate; the deliberate invalid ones must not."""
    from pydantic import ValidationError

    data = json.loads(DATASET.read_text(encoding="utf-8"))
    for case in data["cases"]:
        for step in case["steps"]:
            if any(isinstance(v, dict) for v in step["args"].values()):
                continue  # contains a $ref resolved at run time
            expects_error = any(e["path"] == "ok" and e.get("equals") is False for e in step["expect"])
            if expects_error:
                with pytest.raises(ValidationError):
                    SCHEMAS[step["tool"]].model_validate(step["args"])
            else:
                SCHEMAS[step["tool"]].model_validate(step["args"])
