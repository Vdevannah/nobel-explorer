"""Validated semantic retrieval over the Nobel knowledge index.

Score semantics
---------------
``distance``   cosine distance from ChromaDB. LOWER = more similar (0 = same
               direction, 1 = orthogonal, 2 = opposite).
``similarity`` 1 - distance, i.e. cosine similarity. HIGHER = more similar.

Results are nearest neighbours, not verified evidence. A query with no
relevant content in the knowledge base still returns its k closest chunks;
callers must judge relevance (``min_similarity`` can drop weak matches).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field

from backend.ai.config import (
    CITATION_SOURCE_LINKED,
    EDUCATIONAL_LEVELS,
    RetrievalConfig,
)
from backend.services.exceptions import ServiceValidationError

SCORE_SEMANTICS = (
    "distance is cosine distance (lower = more similar); "
    "similarity = 1 - distance (higher = more similar)"
)
EVIDENCE_NOTE = (
    "Nearest-neighbour matches are not automatically relevant evidence. "
    "Check similarity and content; educational explanations are unverified."
)


class SearchValidationError(ServiceValidationError):
    """Invalid retrieval input (maps to HTTP 400 in the existing app)."""


class SourceInfo(BaseModel):
    name: str
    url: str


class SearchResult(BaseModel):
    rank: int
    doc_id: str
    chunk_id: str
    doc_type: str
    title: str
    text: str
    distance: float
    similarity: float
    citation_status: str
    source: SourceInfo | None = None
    related_source: SourceInfo | None = Field(
        default=None,
        description="Parent contribution source; context only, not a citation for this text.",
    )
    metadata: dict[str, Any]


class SearchResponse(BaseModel):
    query: str
    filters: dict[str, Any]
    k: int
    results: list[SearchResult]
    dropped_below_min_similarity: int = 0
    score_semantics: str = SCORE_SEMANTICS
    evidence_note: str = EVIDENCE_NOTE
    message: str | None = None


def _normalise_level(level: str | None) -> str | None:
    if level is None:
        return None
    if not isinstance(level, str):
        raise SearchValidationError("level must be a string")
    lookup = {name.lower(): name for name in EDUCATIONAL_LEVELS}
    canonical = lookup.get(level.strip().lower())
    if canonical is None:
        raise SearchValidationError(f"level must be one of {', '.join(EDUCATIONAL_LEVELS)}")
    return canonical


def _validate(
    query: Any, level: Any, laureate_id: Any, k: Any, min_similarity: Any, config: RetrievalConfig,
) -> tuple[str, str | None, int | None, int]:
    if not isinstance(query, str) or not query.strip():
        raise SearchValidationError("query must be a non-empty string")
    query = " ".join(query.split())
    if len(query) > config.max_query_chars:
        raise SearchValidationError(f"query must be at most {config.max_query_chars} characters")

    level = _normalise_level(level)

    if laureate_id is not None:
        if isinstance(laureate_id, bool) or not isinstance(laureate_id, int) or laureate_id <= 0:
            raise SearchValidationError("laureate_id must be a positive integer")

    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= config.max_k:
        raise SearchValidationError(f"k must be an integer between 1 and {config.max_k}")

    if min_similarity is not None:
        if isinstance(min_similarity, bool) or not isinstance(min_similarity, (int, float)) or not -1 <= min_similarity <= 1:
            raise SearchValidationError("min_similarity must be a number between -1 and 1")
    return query, level, laureate_id, k


def _build_where(level: str | None, laureate_id: int | None) -> dict[str, Any] | None:
    clauses: list[dict[str, Any]] = []
    if level is not None:
        clauses.append({"level": level})
    if laureate_id is not None:
        clauses.append({"laureate_ids": {"$contains": laureate_id}})
    if not clauses:
        return None
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


@lru_cache(maxsize=1)
def get_default_store():
    """Process-wide store backed by the real Sentence Transformer model."""
    from backend.ai.embeddings import SentenceTransformerEmbedder
    from backend.ai.vector_store import NobelVectorStore

    return NobelVectorStore(SentenceTransformerEmbedder())


def search_nobel_knowledge(
    query: str,
    level: str | None = None,
    laureate_id: int | None = None,
    k: int = 5,
    *,
    min_similarity: float | None = None,
    store=None,
    config: RetrievalConfig | None = None,
) -> SearchResponse:
    """Semantic search over laureate records and educational content.

    ``level`` restricts results to educational explanations at that level.
    ``laureate_id`` (internal Nobel Explorer id) restricts results to chunks
    credited to that laureate. ``k`` is capped at ``RetrievalConfig.max_k``.
    """
    config = config or RetrievalConfig()
    query, level, laureate_id, k = _validate(query, level, laureate_id, k, min_similarity, config)
    filters = {key: value for key, value in (("level", level), ("laureate_id", laureate_id)) if value is not None}

    store = store or get_default_store()
    if store.count() == 0:
        return SearchResponse(query=query, filters=filters, k=k, results=[],
                              message="The knowledge index is empty. Run the index builder first.")

    raw = store.query(store.embedder.embed_query(query), k=k, where=_build_where(level, laureate_id))
    ids = raw["ids"][0] if raw.get("ids") else []

    results: list[SearchResult] = []
    dropped = 0
    for chunk_id, text, metadata, distance in zip(
        ids, raw["documents"][0], raw["metadatas"][0], raw["distances"][0]
    ):
        metadata = dict(metadata or {})
        similarity = 1.0 - float(distance)
        if min_similarity is not None and similarity < min_similarity:
            dropped += 1
            continue
        source = None
        if metadata.get("citation_status") == CITATION_SOURCE_LINKED and metadata.get("source_url"):
            source = SourceInfo(name=metadata.get("source_name", ""), url=metadata["source_url"])
        related = None
        if metadata.get("related_source_url"):
            related = SourceInfo(name=metadata.get("related_source_name", ""), url=metadata["related_source_url"])
        results.append(SearchResult(
            rank=len(results) + 1,
            doc_id=metadata.get("parent_doc_id", chunk_id.split("#", 1)[0]),
            chunk_id=chunk_id,
            doc_type=metadata.get("doc_type", "unknown"),
            title=metadata.get("title", ""),
            text=text or "",
            distance=round(float(distance), 6),
            similarity=round(similarity, 6),
            citation_status=metadata.get("citation_status", "unknown"),
            source=source,
            related_source=related,
            metadata=metadata,
        ))

    message = None
    if not results:
        message = (
            "No chunks matched the filters." if not dropped
            else f"No results met min_similarity={min_similarity}."
        )
    return SearchResponse(query=query, filters=filters, k=k, results=results,
                          dropped_below_min_similarity=dropped, message=message)
