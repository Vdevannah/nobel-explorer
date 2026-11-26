"""Persistent ChromaDB storage for Nobel knowledge chunks.

* Cosine distance is configured explicitly (``configuration.hnsw.space``).
  Chroma reports cosine *distance* = 1 - cosine similarity: LOWER is closer.
* The collection records the embedding fingerprint (model, revision,
  dimension, normalisation). Opening it with a different embedder raises
  ``EmbeddingModelMismatchError`` instead of silently mixing vector spaces.
* ``sync`` is idempotent: unchanged chunks (same id + content hash) are not
  re-embedded, changed chunks are upserted, and chunks whose source records
  disappeared are deleted. It must be called with the FULL current corpus.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from backend.ai.chunking import Chunk
from backend.ai.config import IndexConfig
from backend.ai.embeddings import Embedder

INDEX_SCHEMA_VERSION = 1
_ALLOWED_SCALARS = (str, int, float, bool)


class EmbeddingModelMismatchError(RuntimeError):
    pass


class MetadataValidationError(ValueError):
    pass


def validate_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Return Chroma-compatible metadata or raise.

    Chroma 1.5 accepts str/int/float/bool scalars and non-empty homogeneous
    lists of those. ``None`` values are silently dropped by Chroma, so they
    are rejected here to keep stored metadata explicit.
    """
    clean: dict[str, Any] = {}
    for key, value in metadata.items():
        if not isinstance(key, str) or not key:
            raise MetadataValidationError(f"invalid metadata key {key!r}")
        if value is None:
            raise MetadataValidationError(f"metadata {key!r} is None; omit the key instead")
        if isinstance(value, list):
            if not value:
                raise MetadataValidationError(f"metadata {key!r} is an empty list")
            kinds = {type(v) for v in value}
            if len(kinds) != 1 or not issubclass(next(iter(kinds)), _ALLOWED_SCALARS):
                raise MetadataValidationError(f"metadata {key!r} must be a homogeneous scalar list")
        elif not isinstance(value, _ALLOWED_SCALARS):
            raise MetadataValidationError(f"metadata {key!r} has unsupported type {type(value).__name__}")
        clean[key] = value
    return clean


@dataclass(frozen=True)
class SyncResult:
    added: int
    updated: int
    unchanged: int
    deleted: int
    total: int
    embedded: int
    embed_seconds: float


class NobelVectorStore:
    def __init__(self, embedder: Embedder, config: IndexConfig | None = None):
        import chromadb
        from chromadb.config import Settings

        self.embedder = embedder
        self.config = config or IndexConfig()
        self.config.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(self.config.persist_dir),
            settings=Settings(anonymized_telemetry=False, allow_reset=False),
        )
        self._collection = None

    # -- collection lifecycle ----------------------------------------------
    def _expected_metadata(self) -> dict[str, Any]:
        return {**self.embedder.fingerprint(), "index_schema_version": INDEX_SCHEMA_VERSION}

    def _exists(self) -> bool:
        names = [c if isinstance(c, str) else c.name for c in self.client.list_collections()]
        return self.config.collection_name in names

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self._open()
        return self._collection

    def _open(self):
        expected = self._expected_metadata()
        if self._exists():
            collection = self.client.get_collection(self.config.collection_name, embedding_function=None)
            stored = collection.metadata or {}
            mismatched = {
                key: (stored.get(key), value)
                for key, value in expected.items()
                if stored.get(key) != value
            }
            if mismatched:
                raise EmbeddingModelMismatchError(
                    f"Collection '{self.config.collection_name}' was built with a different "
                    f"embedding configuration {mismatched}. Rebuild the index (--rebuild)."
                )
            space = (collection.configuration_json.get("hnsw") or {}).get("space")
            if space != self.config.distance_space:
                raise EmbeddingModelMismatchError(
                    f"Collection distance space is {space!r}, expected {self.config.distance_space!r}"
                )
            return collection
        return self.client.create_collection(
            self.config.collection_name,
            configuration={"hnsw": {"space": self.config.distance_space}},
            metadata=expected,
            embedding_function=None,
        )

    def reset_collection(self) -> None:
        if self._exists():
            self.client.delete_collection(self.config.collection_name)
        self._collection = None

    def count(self) -> int:
        return self.collection.count()

    def distance_space(self) -> str:
        return (self.collection.configuration_json.get("hnsw") or {}).get("space")

    # -- writes -------------------------------------------------------------
    def sync(self, chunks: list[Chunk]) -> SyncResult:
        ids = [c.chunk_id for c in chunks]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate chunk ids in input")

        existing = self.collection.get(include=["metadatas"])
        existing_hash = {
            cid: (meta or {}).get("content_hash")
            for cid, meta in zip(existing["ids"], existing["metadatas"])
        }

        pending = [c for c in chunks if existing_hash.get(c.chunk_id) != c.metadata["content_hash"]]
        added = sum(1 for c in pending if c.chunk_id not in existing_hash)
        updated = len(pending) - added
        stale = sorted(set(existing_hash) - set(ids))

        started = time.perf_counter()
        embeddings = self.embedder.embed_documents([c.text for c in pending])
        embed_seconds = time.perf_counter() - started
        expected_dim = self.embedder.dimension
        bad = next((len(v) for v in embeddings if len(v) != expected_dim), None)
        if bad is not None:
            raise ValueError(f"Embedding dimension {bad} != {expected_dim}")

        batch = max(1, min(self.client.get_max_batch_size(), 1000))
        for start in range(0, len(pending), batch):
            part = pending[start:start + batch]
            self.collection.upsert(
                ids=[c.chunk_id for c in part],
                embeddings=embeddings[start:start + batch],
                documents=[c.text for c in part],
                metadatas=[validate_metadata(c.metadata) for c in part],
            )
        for start in range(0, len(stale), batch):
            self.collection.delete(ids=stale[start:start + batch])

        return SyncResult(
            added=added,
            updated=updated,
            unchanged=len(chunks) - len(pending),
            deleted=len(stale),
            total=self.collection.count(),
            embedded=len(pending),
            embed_seconds=round(embed_seconds, 3),
        )

    # -- reads --------------------------------------------------------------
    def query(self, embedding: list[float], k: int, where: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.collection.query(
            query_embeddings=[embedding],
            n_results=k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
