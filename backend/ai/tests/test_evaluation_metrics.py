"""Hand-calculated checks for the retrieval evaluation metrics."""

import json
from pathlib import Path

import pytest

from backend.ai.evaluation.run_retrieval_eval import (
    DATASET,
    first_relevant_rank,
    hit_at_k,
    recall_at_k,
    reciprocal_rank,
)

# Chunk-level ranking already mapped to parent doc ids (note the duplicate).
RANKED = ["connection:25", "explanation:38:expert", "connection:24",
          "explanation:38:expert", "connection:26", "contribution:38"]
RELEVANT = {"contribution:38", "explanation:38:simple", "explanation:38:explore",
            "explanation:38:advanced", "explanation:38:expert"}


def test_hit_at_k():
    assert hit_at_k(RANKED, RELEVANT, 3) is True      # rank 2 is relevant
    assert hit_at_k(RANKED, RELEVANT, 1) is False
    assert hit_at_k([], RELEVANT, 3) is False


def test_recall_counts_documents_once_even_if_chunks_repeat():
    # Top-5 contains explanation:38:expert twice -> 1 distinct relevant doc of 5.
    assert recall_at_k(RANKED, RELEVANT, 5) == pytest.approx(1 / 5)
    # Top-6 adds contribution:38 -> 2 of 5.
    assert recall_at_k(RANKED, RELEVANT, 6) == pytest.approx(2 / 5)


def test_recall_rejects_empty_relevant_set():
    with pytest.raises(ValueError):
        recall_at_k(RANKED, set(), 5)


def test_reciprocal_rank_and_cutoff():
    assert first_relevant_rank(RANKED, RELEVANT, 10) == 2
    assert reciprocal_rank(RANKED, RELEVANT, 10) == pytest.approx(0.5)
    assert reciprocal_rank(RANKED, RELEVANT, 1) == 0.0          # outside cutoff
    assert reciprocal_rank(["x", "y"], {"z"}, 10) == 0.0


def test_mean_reciprocal_rank_example():
    # Three questions with first relevant ranks 1, 3 and none -> (1 + 1/3 + 0) / 3.
    rrs = [reciprocal_rank(["a"], {"a"}, 10),
           reciprocal_rank(["x", "y", "a"], {"a"}, 10),
           reciprocal_rank(["x"], {"a"}, 10)]
    assert sum(rrs) / len(rrs) == pytest.approx(4 / 9)


def test_evaluation_dataset_is_well_formed():
    data = json.loads(Path(DATASET).read_text(encoding="utf-8"))
    in_scope, out_of_scope = data["in_scope"], data["out_of_scope"]
    assert len(in_scope) >= 15 and len(out_of_scope) >= 5
    assert len({q["id"] for q in in_scope + out_of_scope}) == len(in_scope) + len(out_of_scope)
    for question in in_scope:
        assert 1 <= len(question["relevant"]) <= 5
        assert question.get("level") in (None, "Simple", "Explore", "Advanced", "Expert")
    topics = {q["topic"] for q in in_scope}
    assert {"photoelectric", "relativity", "mrna", "click", "motivation"} <= topics
