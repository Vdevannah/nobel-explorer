"""Configuration for the retrieval pipeline.

Every value can be overridden through an environment variable so the same
code runs locally, in tests (temporary directories) and later in deployment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

EDUCATIONAL_LEVELS: tuple[str, ...] = ("Simple", "Explore", "Advanced", "Expert")

DOC_TYPES: tuple[str, ...] = (
    "laureate_record",
    "contribution",
    "explanation",
    "connection",
)

# Citation status vocabulary. These describe provenance, not truth.
CITATION_SOURCE_LINKED = "source_linked"
"""Record stores its own source name/URL (contribution, connection).
The URL is a reference page for the record; individual claims are not
verified sentence by sentence."""

CITATION_STRUCTURED_RECORD = "structured_record"
"""Structured fields imported from the official Nobel Prize API by the ETL
pipeline. No per-record URL is stored, so none is reported."""

CITATION_UNVERIFIED_EDUCATIONAL = "unverified_educational"
"""Authored educational explanation with no stored citation. The parent
contribution's source is exposed separately as ``related_source_*`` and
must not be presented as a citation for the explanation text."""

CITATION_STATUSES = (
    CITATION_SOURCE_LINKED,
    CITATION_STRUCTURED_RECORD,
    CITATION_UNVERIFIED_EDUCATIONAL,
)


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value not in (None, "") else default


@dataclass(frozen=True)
class EmbeddingConfig:
    model_name: str = field(
        default_factory=lambda: os.getenv(
            "AI_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        )
    )
    # Optional pinned Hugging Face commit; None means "latest cached/remote".
    revision: str | None = field(
        default_factory=lambda: os.getenv("AI_EMBEDDING_REVISION") or None
    )
    normalize_embeddings: bool = True
    batch_size: int = field(default_factory=lambda: _env_int("AI_EMBEDDING_BATCH_SIZE", 64))
    device: str = field(default_factory=lambda: os.getenv("AI_EMBEDDING_DEVICE", "cpu"))


@dataclass(frozen=True)
class ChunkingConfig:
    chunk_size: int = field(default_factory=lambda: _env_int("AI_CHUNK_SIZE", 900))
    chunk_overlap: int = field(default_factory=lambda: _env_int("AI_CHUNK_OVERLAP", 150))
    # Hard ceiling in model tokens, including [CLS]/[SEP]. all-MiniLM-L6-v2
    # truncates input beyond max_seq_length=256, so chunks must stay below it.
    max_tokens: int = field(default_factory=lambda: _env_int("AI_CHUNK_MAX_TOKENS", 256))

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if not 0 <= self.chunk_overlap < self.chunk_size:
            raise ValueError("chunk_overlap must be >= 0 and < chunk_size")
        if self.max_tokens <= 8:
            raise ValueError("max_tokens is unrealistically small")


@dataclass(frozen=True)
class IndexConfig:
    persist_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("AI_CHROMA_DIR", str(REPO_ROOT / "ai_index" / "chroma"))
        )
    )
    collection_name: str = field(
        default_factory=lambda: os.getenv("AI_CHROMA_COLLECTION", "nobel_knowledge")
    )
    distance_space: str = "cosine"


@dataclass(frozen=True)
class RetrievalConfig:
    default_k: int = 5
    max_k: int = 10
    max_query_chars: int = 500
