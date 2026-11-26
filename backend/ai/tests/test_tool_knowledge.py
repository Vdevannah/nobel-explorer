"""search_nobel_knowledge tool, document de-duplication and weak-match flags.

Uses the HashingEmbedder (lexical, NOT semantic): these tests check
behaviour and contracts, not retrieval quality.
"""

import pytest

pytest.importorskip("langchain_core")
pytest.importorskip("chromadb")

from backend.ai.retrieval import SearchValidationError, search_nobel_knowledge  # noqa: E402

PHOTON_QUERY = "photon energy frequency work function electron emission"


def test_knowledge_tool_returns_compact_serialisable_results(tools):
    result = tools["search_nobel_knowledge"].invoke({"query": "click chemistry buckles", "k": 3})
    assert result["ok"] is True
    data = result["data"]
    assert data["returned"] <= 3 and data["dedupe_by_document"] is True
    first = data["results"][0]
    assert set(first) == {"rank", "doc_id", "chunk_id", "doc_type", "title", "text", "similarity", "distance",
                          "weak_match", "citation_status", "source", "related_source", "metadata"}
    assert first["distance"] == pytest.approx(1 - first["similarity"], abs=1e-4)
    assert "content_hash" not in first["metadata"] and "token_count" not in first["metadata"]
    assert "not instructions" in data["content_policy"]
    assert "lower = more similar" in data["score_semantics"]
    assert data["weak_match_threshold"] == 0.40 and "not a calibrated" in data["weak_match_note"]


def test_knowledge_tool_preserves_citation_distinctions(tools):
    data = tools["search_nobel_knowledge"].invoke({"query": "photons electrons metal", "k": 10})["data"]
    by_status = {}
    for r in data["results"]:
        by_status.setdefault(r["citation_status"], []).append(r)
    for r in by_status.get("unverified_educational", []):
        assert r["source"] is None
    for r in by_status.get("source_linked", []):
        assert r["source"]["url"].startswith("https://")
    for r in by_status.get("structured_record", []):
        assert r["source"] is None and r["related_source"] is None
    assert by_status.get("unverified_educational") and by_status.get("source_linked")


def test_knowledge_tool_filters(tools):
    data = tools["search_nobel_knowledge"].invoke({"query": "molecules", "level": "explore", "laureate_id": 886})["data"]
    assert data["filters"] == {"level": "Explore", "laureate_id": 886}
    assert data["results"] and all(r["metadata"]["level"] == "Explore" for r in data["results"])
    assert all(886 in r["metadata"]["laureate_ids"] for r in data["results"])


def test_knowledge_tool_invalid_input(tools):
    for args in ({"query": ""}, {"query": "ok", "k": 50}, {"query": "ok", "level": "Beginner"}):
        result = tools["search_nobel_knowledge"].invoke(args)
        assert result["ok"] is False and result["error"]["type"] == "validation_error"


def test_knowledge_tool_empty_filtered_results(tools):
    data = tools["search_nobel_knowledge"].invoke({"query": "anything", "laureate_id": 999999})["data"]
    assert data["results"] == [] and data["message"] and data["all_results_weak"] is None


# ---------------------------------------------------------------- de-duplication

def test_default_retrieval_behaviour_is_unchanged(tool_store):
    response = search_nobel_knowledge(PHOTON_QUERY, k=10, store=tool_store)
    assert response.dedupe_by_document is False
    doc_ids = [r.doc_id for r in response.results]
    assert len(doc_ids) != len(set(doc_ids))  # the multi-chunk Expert explanation repeats


def test_dedupe_keeps_highest_ranked_chunk_per_document(tool_store):
    baseline = search_nobel_knowledge(PHOTON_QUERY, k=10, store=tool_store)
    deduped = search_nobel_knowledge(PHOTON_QUERY, k=10, store=tool_store, dedupe_by_document=True)
    doc_ids = [r.doc_id for r in deduped.results]
    assert len(doc_ids) == len(set(doc_ids))
    first_chunk = {}
    for r in baseline.results:
        first_chunk.setdefault(r.doc_id, r.chunk_id)
    for r in deduped.results:
        if r.doc_id in first_chunk:
            assert r.chunk_id == first_chunk[r.doc_id]
    assert [r.rank for r in deduped.results] == list(range(1, len(deduped.results) + 1))
    sims = [r.similarity for r in deduped.results]
    assert sims == sorted(sims, reverse=True)
    assert deduped.candidates_considered > len(deduped.results) or len(deduped.results) < 10


def test_dedupe_preserves_metadata(tool_store):
    for r in search_nobel_knowledge(PHOTON_QUERY, k=5, store=tool_store, dedupe_by_document=True).results:
        assert r.metadata["parent_doc_id"] == r.doc_id and "citation_status" in r.metadata


def test_dedupe_returns_fewer_than_k_honestly(tool_store):
    response = search_nobel_knowledge("photons", laureate_id=249, level="Expert", k=5, store=tool_store,
                                      dedupe_by_document=True)
    assert len(response.results) == 1  # one Expert document exists for laureate 249
    assert "Only 1 distinct documents matched" in response.message


def test_dedupe_overfetch_is_bounded(tool_store):
    response = search_nobel_knowledge("nobel", k=10, store=tool_store, dedupe_by_document=True)
    assert response.candidates_considered <= 40


def test_dedupe_flag_validated(tool_store):
    with pytest.raises(SearchValidationError):
        search_nobel_knowledge("photons", store=tool_store, dedupe_by_document="yes")


# ---------------------------------------------------------------- weak matches

def test_weak_match_flags_do_not_discard_results(tool_store):
    strict = search_nobel_knowledge("photons", k=5, store=tool_store, weak_match_threshold=0.99)
    assert len(strict.results) == 5 and all(r.weak_match for r in strict.results)
    assert strict.all_results_weak is True


def test_weak_match_default_threshold_and_disable(tool_store):
    default = search_nobel_knowledge("photons", k=3, store=tool_store)
    assert default.weak_match_threshold == 0.40
    assert all(r.weak_match == (r.similarity < 0.40) for r in default.results)
    disabled = search_nobel_knowledge("photons", k=3, store=tool_store, weak_match_threshold=None)
    assert disabled.weak_match_threshold is None and all(r.weak_match is None for r in disabled.results)
    assert disabled.all_results_weak is None


def test_weak_match_threshold_is_configurable_via_env(monkeypatch, tool_store):
    from backend.ai.config import RetrievalConfig

    monkeypatch.setenv("AI_WEAK_MATCH_THRESHOLD", "0.25")
    assert search_nobel_knowledge("photons", store=tool_store, config=RetrievalConfig()).weak_match_threshold == 0.25


@pytest.mark.parametrize("bad", [2, -2, "0.4", True])
def test_weak_match_threshold_validated(tool_store, bad):
    with pytest.raises(SearchValidationError):
        search_nobel_knowledge("photons", store=tool_store, weak_match_threshold=bad)


def test_min_similarity_behaviour_preserved(tool_store):
    response = search_nobel_knowledge("photons", store=tool_store, min_similarity=0.999)
    assert response.results == [] and response.dropped_below_min_similarity > 0


def test_dedupe_equals_first_occurrence_of_each_document(tool_store):
    # The property behind "Hit@3 / MRR cannot decrease": the de-duplicated list is
    # the first occurrence of every document in the (larger) candidate list.
    from backend.ai.config import RetrievalConfig

    deduped = search_nobel_knowledge(PHOTON_QUERY, k=5, store=tool_store, dedupe_by_document=True,
                                     weak_match_threshold=None)
    candidates = search_nobel_knowledge(PHOTON_QUERY, k=10, store=tool_store, weak_match_threshold=None)
    first = []
    for r in candidates.results:
        if r.doc_id not in first:
            first.append(r.doc_id)
    assert [r.doc_id for r in deduped.results] == first[:5]
    assert RetrievalConfig().dedupe_max_candidates >= RetrievalConfig().max_k


def test_dedupe_never_fetches_fewer_candidates_than_k(tool_store):
    # Regression guard: a misconfigured cap below k must not shrink the candidate
    # pool under the baseline's, or de-duplication could lose relevant documents.
    from backend.ai.config import RetrievalConfig

    tiny_cap = RetrievalConfig(dedupe_overfetch_factor=1, dedupe_max_candidates=2)
    response = search_nobel_knowledge("photons", k=6, store=tool_store, dedupe_by_document=True, config=tiny_cap)
    assert response.candidates_considered >= 6
