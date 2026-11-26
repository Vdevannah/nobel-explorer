"""Vector index tests using the HashingEmbedder (not a semantic model)."""

import dataclasses

import pytest

pytest.importorskip("chromadb")

from backend.ai.chunking import chunk_documents  # noqa: E402
from backend.ai.embeddings import HashingEmbedder  # noqa: E402
from backend.ai.vector_store import (  # noqa: E402
    EmbeddingModelMismatchError,
    MetadataValidationError,
    NobelVectorStore,
    validate_metadata,
)


@pytest.fixture()
def chunks(documents, hashing_embedder):
    return chunk_documents(documents, hashing_embedder.count_tokens)


@pytest.fixture()
def store(hashing_embedder, index_config):
    return NobelVectorStore(hashing_embedder, index_config)


def test_creates_cosine_collection_with_embedding_fingerprint(store, hashing_embedder):
    assert store.distance_space() == "cosine"
    metadata = store.collection.metadata
    assert metadata["embedding_model"] == hashing_embedder.model_id
    assert metadata["embedding_dim"] == 384
    assert metadata["embedding_normalized"] is True


def test_sync_stores_embeddings_text_and_metadata(store, chunks):
    result = store.sync(chunks)
    assert result.added == len(chunks) and result.total == len(chunks)
    stored = store.collection.get(ids=[chunks[0].chunk_id], include=["documents", "metadatas", "embeddings"])
    assert stored["documents"][0] == chunks[0].text
    assert stored["metadatas"][0]["parent_doc_id"] == chunks[0].parent_doc_id
    assert len(stored["embeddings"][0]) == 384


def test_repeated_sync_is_idempotent(store, chunks):
    store.sync(chunks)
    again = store.sync(chunks)
    assert again.added == 0 and again.updated == 0 and again.deleted == 0
    assert again.unchanged == len(chunks)
    assert again.embedded == 0
    assert store.count() == len(chunks)


def test_duplicate_chunk_ids_rejected(store, chunks):
    with pytest.raises(ValueError):
        store.sync([chunks[0], chunks[0]])


def test_index_persists_across_clients(store, chunks, hashing_embedder, index_config):
    store.sync(chunks)
    reopened = NobelVectorStore(hashing_embedder, index_config)
    assert reopened.count() == len(chunks)
    assert reopened.distance_space() == "cosine"


def test_changed_record_is_updated(store, chunks):
    store.sync(chunks)
    target = chunks[0]
    changed = dataclasses.replace(
        target,
        text=target.text + " Updated.",
        metadata={**target.metadata, "content_hash": "changed-hash"},
    )
    result = store.sync([changed, *chunks[1:]])
    assert result.updated == 1 and result.added == 0 and result.embedded == 1
    stored = store.collection.get(ids=[target.chunk_id], include=["documents"])
    assert stored["documents"][0].endswith("Updated.")


def test_removed_record_is_deleted(store, chunks):
    store.sync(chunks)
    result = store.sync(chunks[1:])
    assert result.deleted == 1
    assert store.count() == len(chunks) - 1
    assert store.collection.get(ids=[chunks[0].chunk_id])["ids"] == []


def test_mismatched_embedding_model_is_refused(store, chunks, index_config):
    store.sync(chunks)
    other = HashingEmbedder(model_id="test/a-different-model")
    with pytest.raises(EmbeddingModelMismatchError):
        NobelVectorStore(other, index_config).count()


def test_mismatched_dimension_is_refused(store, chunks, index_config):
    store.sync(chunks)
    with pytest.raises(EmbeddingModelMismatchError):
        NobelVectorStore(HashingEmbedder(dim=128), index_config).count()


def test_reset_allows_rebuild_with_new_model(store, chunks, index_config):
    store.sync(chunks)
    other = NobelVectorStore(HashingEmbedder(model_id="test/new-model"), index_config)
    other.reset_collection()
    assert other.sync(chunks).added == len(chunks)


@pytest.mark.parametrize("bad", [
    {"x": None}, {"x": []}, {"x": [1, "a"]}, {"x": {"nested": 1}}, {"": 1},
])
def test_invalid_metadata_rejected(bad):
    with pytest.raises(MetadataValidationError):
        validate_metadata(bad)


def test_valid_metadata_accepted(chunks):
    for chunk in chunks:
        assert validate_metadata(chunk.metadata) == chunk.metadata
