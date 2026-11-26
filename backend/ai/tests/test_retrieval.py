"""Retrieval tests using the HashingEmbedder (lexical, not semantic)."""

import pytest

pytest.importorskip("chromadb")

from backend.ai.chunking import chunk_documents  # noqa: E402
from backend.ai.retrieval import SearchValidationError, search_nobel_knowledge  # noqa: E402
from backend.ai.vector_store import NobelVectorStore  # noqa: E402
from backend.services.exceptions import ServiceValidationError  # noqa: E402


@pytest.fixture()
def store(documents, hashing_embedder, index_config):
    store = NobelVectorStore(hashing_embedder, index_config)
    store.sync(chunk_documents(documents, hashing_embedder.count_tokens))
    return store


def test_returns_relevant_result_with_scores(store):
    response = search_nobel_knowledge("click chemistry bioorthogonal reactions", store=store)
    assert response.results
    top = response.results[0]
    assert "779" in top.doc_id or top.metadata.get("contribution_id") == 779
    for result in response.results:
        assert result.distance == pytest.approx(1 - result.similarity, abs=1e-6)
    distances = [r.distance for r in response.results]
    assert distances == sorted(distances)  # lower distance ranks first
    assert "lower = more similar" in response.score_semantics


def test_result_shape(store):
    result = search_nobel_knowledge("photoelectric effect", k=3, store=store).results[0]
    assert result.rank == 1
    assert result.chunk_id.startswith(result.doc_id + "#c")
    assert result.text and result.title and result.doc_type
    assert result.citation_status in {"source_linked", "structured_record", "unverified_educational"}


def test_level_filter(store):
    response = search_nobel_knowledge("photons electrons metal", level="simple", store=store)
    assert response.filters == {"level": "Simple"}
    assert response.results
    assert all(r.metadata["level"] == "Simple" and r.doc_type == "explanation" for r in response.results)


def test_laureate_filter(store):
    response = search_nobel_knowledge("chemistry", laureate_id=766, k=10, store=store)
    assert response.results
    assert all(766 in r.metadata["laureate_ids"] for r in response.results)


def test_combined_filters(store):
    response = search_nobel_knowledge("light", level="Expert", laureate_id=249, store=store)
    assert response.results
    assert all(r.metadata["level"] == "Expert" and 249 in r.metadata["laureate_ids"] for r in response.results)


def test_filters_with_no_matches_return_empty_with_message(store):
    response = search_nobel_knowledge("photons", level="Expert", laureate_id=766, store=store)
    assert response.results == []
    assert response.message


def test_unknown_laureate_returns_empty(store):
    assert search_nobel_knowledge("anything", laureate_id=999999, store=store).results == []


def test_explanations_expose_related_source_not_citation(store):
    response = search_nobel_knowledge("photons", level="Simple", laureate_id=249, store=store)
    result = response.results[0]
    assert result.citation_status == "unverified_educational"
    assert result.source is None
    assert result.related_source is not None


def test_source_linked_results_expose_source(store):
    response = search_nobel_knowledge("solar panels photovoltaic", store=store)
    linked = [r for r in response.results if r.citation_status == "source_linked"]
    assert linked and all(r.source and r.source.url.startswith("https://") for r in linked)


def test_k_is_respected_and_capped(store):
    assert len(search_nobel_knowledge("nobel", k=2, store=store).results) == 2
    with pytest.raises(SearchValidationError):
        search_nobel_knowledge("nobel", k=11, store=store)


def test_min_similarity_drops_weak_matches(store):
    response = search_nobel_knowledge("photoelectric", min_similarity=0.99, store=store)
    assert response.results == [] and response.dropped_below_min_similarity > 0
    assert "min_similarity" in response.message


def test_empty_index_is_handled(hashing_embedder, tmp_path):
    from backend.ai.config import IndexConfig

    empty = NobelVectorStore(hashing_embedder, IndexConfig(persist_dir=tmp_path / "empty", collection_name="empty"))
    response = search_nobel_knowledge("photoelectric", store=empty)
    assert response.results == [] and "empty" in response.message


@pytest.mark.parametrize("kwargs", [
    {"query": ""}, {"query": "   "}, {"query": None}, {"query": 42}, {"query": "x" * 501},
    {"query": "ok", "level": "Beginner"}, {"query": "ok", "level": 3},
    {"query": "ok", "laureate_id": 0}, {"query": "ok", "laureate_id": -5},
    {"query": "ok", "laureate_id": "249"}, {"query": "ok", "laureate_id": True},
    {"query": "ok", "k": 0}, {"query": "ok", "k": "5"}, {"query": "ok", "k": True},
    {"query": "ok", "min_similarity": 2},
])
def test_invalid_input_rejected(store, kwargs):
    with pytest.raises(SearchValidationError):
        search_nobel_knowledge(store=store, **kwargs)


def test_validation_error_maps_to_existing_http_400_handler():
    assert issubclass(SearchValidationError, ServiceValidationError)


def test_query_whitespace_is_normalised(store):
    assert search_nobel_knowledge("  click   chemistry ", store=store).query == "click chemistry"
