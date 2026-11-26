"""Embedding backends.

``SentenceTransformerEmbedder`` runs ``sentence-transformers/all-MiniLM-L6-v2``
locally on CPU (no paid APIs, no fine-tuning). The same instance and the same
settings are used for documents and queries.

``HashingEmbedder`` is a deterministic bag-of-words stand-in for fast unit
tests. It is NOT a semantic model and results obtained with it must never be
reported as real-model validation.
"""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Protocol

from backend.ai.config import EmbeddingConfig


class Embedder(Protocol):
    model_id: str

    @property
    def dimension(self) -> int: ...

    def fingerprint(self) -> dict[str, str | int | bool]: ...

    def count_tokens(self, text: str) -> int: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class SentenceTransformerEmbedder:
    def __init__(self, config: EmbeddingConfig | None = None):
        self.config = config or EmbeddingConfig()
        self.model_id = self.config.model_name
        self._model = None
        self._revision: str | None = None

    # -- lazy model ---------------------------------------------------------
    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                self.config.model_name,
                revision=self.config.revision,
                device=self.config.device,
            )
            self._revision = self._resolve_revision()
        return self._model

    def _resolve_revision(self) -> str:
        if self.config.revision:
            return self.config.revision
        try:
            from huggingface_hub import snapshot_download

            path = snapshot_download(self.config.model_name, local_files_only=True)
            return Path(path).name
        except Exception:  # pragma: no cover - offline / unusual cache layouts
            return "unknown"

    @property
    def revision(self) -> str:
        _ = self.model
        return self._revision or "unknown"

    @property
    def dimension(self) -> int:
        model = self.model
        getter = getattr(model, "get_embedding_dimension", None) or model.get_sentence_embedding_dimension
        return int(getter())

    @property
    def max_seq_length(self) -> int:
        return int(self.model.max_seq_length)

    def fingerprint(self) -> dict[str, str | int | bool]:
        return {
            "embedding_model": self.model_id,
            "embedding_revision": self.revision,
            "embedding_dim": self.dimension,
            "embedding_normalized": self.config.normalize_embeddings,
            "embedding_max_seq_length": self.max_seq_length,
        }

    # -- operations ---------------------------------------------------------
    def count_tokens(self, text: str) -> int:
        """Token count including [CLS]/[SEP], without truncation."""
        encoded = self.model.tokenizer(
            text, add_special_tokens=True, truncation=False, verbose=False
        )
        return len(encoded["input_ids"])

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode(
            texts,
            batch_size=self.config.batch_size,
            normalize_embeddings=self.config.normalize_embeddings,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


_WORD = re.compile(r"[a-z0-9]+")
_TOKEN = re.compile(r"\w+|[^\w\s]")


class HashingEmbedder:
    """Deterministic feature-hashing embedder for unit tests only."""

    def __init__(self, dim: int = 384, model_id: str = "test/hashing-bag-of-words"):
        self._dim = dim
        self.model_id = model_id

    @property
    def dimension(self) -> int:
        return self._dim

    def fingerprint(self) -> dict[str, str | int | bool]:
        return {
            "embedding_model": self.model_id,
            "embedding_revision": "v1",
            "embedding_dim": self._dim,
            "embedding_normalized": True,
            "embedding_max_seq_length": 256,
        }

    def count_tokens(self, text: str) -> int:
        return len(_TOKEN.findall(text)) + 2

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        for word in _WORD.findall(text.lower()):
            digest = hashlib.md5(word.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self._dim
            vec[index] += 1.0 if digest[4] % 2 == 0 else -1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)
