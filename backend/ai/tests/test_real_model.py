"""Integration tests with the REAL sentence-transformers/all-MiniLM-L6-v2 model.

Opt-in: AI_RUN_REAL_MODEL_TESTS=1. Uses a temporary ChromaDB directory and
the SQLite fixture data (no MySQL needed).
"""

import math

import pytest

pytestmark = pytest.mark.real_model


@pytest.fixture(scope="module")
def real_embedder():
    pytest.importorskip("sentence_transformers")
    from backend.ai.embeddings import SentenceTransformerEmbedder

    return SentenceTransformerEmbedder()


def test_model_identity_and_dimensions(real_embedder):
    fingerprint = real_embedder.fingerprint()
    assert fingerprint["embedding_model"] == "sentence-transformers/all-MiniLM-L6-v2"
    assert fingerprint["embedding_dim"] == 384
    assert fingerprint["embedding_normalized"] is True
    assert fingerprint["embedding_max_seq_length"] == 256
    assert len(fingerprint["embedding_revision"]) == 40  # resolved HF commit hash


def test_embeddings_are_384d_and_unit_normalised(real_embedder):
    vectors = real_embedder.embed_documents(["Photons eject electrons.", "Click chemistry joins molecules."])
    assert len(vectors) == 2
    for vector in vectors:
        assert len(vector) == 384
        assert math.isclose(math.sqrt(sum(v * v for v in vector)), 1.0, rel_tol=1e-4)


def test_query_and_document_use_same_configuration(real_embedder):
    text = "How does light knock electrons out of a metal?"
    query_vec = real_embedder.embed_query(text)
    doc_vec = real_embedder.embed_documents([text])[0]
    assert max(abs(a - b) for a, b in zip(query_vec, doc_vec)) < 1e-5


def test_token_counter_matches_model_tokenizer(real_embedder):
    text = "Einstein explained the photoelectric effect."
    ids = real_embedder.model.tokenizer(text)["input_ids"]
    assert real_embedder.count_tokens(text) == len(ids)
    long_text = "photon " * 400
    assert real_embedder.count_tokens(long_text) > 256  # counted, not truncated


def test_chunks_fit_real_tokenizer_limit(documents, real_embedder):
    from backend.ai.chunking import chunk_documents

    chunks = chunk_documents(documents, real_embedder.count_tokens)
    assert chunks
    assert max(c.token_count for c in chunks) <= real_embedder.max_seq_length


def test_semantic_retrieval_with_paraphrase(documents, real_embedder, index_config):
    pytest.importorskip("chromadb")
    from backend.ai.chunking import chunk_documents
    from backend.ai.retrieval import search_nobel_knowledge
    from backend.ai.vector_store import NobelVectorStore

    store = NobelVectorStore(real_embedder, index_config)
    store.sync(chunk_documents(documents, real_embedder.count_tokens))

    # No shared keywords with "photoelectric": requires semantic matching.
    response = search_nobel_knowledge("why does shining light on metal release charged particles", k=3, store=store)
    assert any(r.metadata.get("contribution_id") == 38 or r.doc_id == "laureate:nobel-26" for r in response.results)

    response = search_nobel_knowledge("snapping molecules together like seat-belt buckles", k=3, store=store)
    assert response.results[0].metadata.get("contribution_id") == 779
