"""Deterministic, token-aware chunking.

Rules
-----
* Records that already fit (``len(text) <= chunk_size`` and within the token
  ceiling) stay intact as a single chunk.
* Longer text is split on sentence / line boundaries and greedily packed up
  to ``chunk_size`` characters. Consecutive chunks share trailing sentences
  (up to ``chunk_overlap`` characters; falls back to trailing words when a
  single sentence is longer than the overlap budget).
* Every chunk is measured with the embedding model's tokenizer (including
  special tokens). If a packed chunk exceeds ``max_tokens`` the character
  budget is reduced and packing restarts, so nothing is silently truncated.
  If a chunk still cannot fit, ``ChunkTooLongError`` is raised.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from backend.ai.config import ChunkingConfig
from backend.ai.documents import SourceDocument

TokenCounter = Callable[[str], int]

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])|\n+")

# Explanation bodies do not repeat their topic, so each chunk is prefixed
# with the document title to keep it self-describing for retrieval.
_HEADER_DOC_TYPES = {"explanation"}


class ChunkTooLongError(ValueError):
    pass


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    parent_doc_id: str
    chunk_index: int
    chunk_count: int
    text: str
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


def _split_units(text: str) -> list[str]:
    return [u.strip() for u in _SENTENCE_BOUNDARY.split(text) if u and u.strip()]


def _split_long_unit(unit: str, limit: int) -> list[str]:
    """Split a single over-long sentence on word boundaries."""
    words, pieces, current = unit.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > limit:
            pieces.append(current)
            current = word
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces


def _overlap_tail(units: list[str], budget: int) -> list[str]:
    tail: list[str] = []
    # Never carry the whole previous chunk forward; that would not progress.
    for unit in reversed(units[1:]):
        if len(" ".join([unit, *tail])) > budget:
            break
        tail.insert(0, unit)
    if not tail and units and budget > 0:
        words = units[-1].split()
        kept: list[str] = []
        for word in reversed(words):
            if len(" ".join([word, *kept])) > budget:
                break
            kept.insert(0, word)
        if kept and len(kept) < len(words):
            tail = [" ".join(kept)]
    return tail


def _pack(units: list[str], chunk_size: int, overlap: int) -> list[str]:
    expanded: list[str] = []
    for unit in units:
        expanded.extend(_split_long_unit(unit, chunk_size) if len(unit) > chunk_size else [unit])

    chunks: list[list[str]] = []
    current: list[str] = []
    new_in_current = 0
    for unit in expanded:
        candidate_len = len(" ".join([*current, unit]))
        if current and new_in_current and candidate_len > chunk_size:
            chunks.append(current)
            current = _overlap_tail(current, overlap)
            # Drop overlap if it would leave no room for the new unit.
            while current and len(" ".join([*current, unit])) > chunk_size:
                current = current[1:]
            new_in_current = 0
        current.append(unit)
        new_in_current += 1
    if current and new_in_current:
        chunks.append(current)
    return [" ".join(c) for c in chunks]


def _render(doc: SourceDocument, body: str, index: int) -> str:
    """The exact text that is embedded and token-counted for a chunk.

    Explanations always get a title header; other document types are
    self-describing, so only their continuation chunks get one.
    """
    if doc.doc_type in _HEADER_DOC_TYPES:
        return f"{doc.title}:\n{body}"
    if index > 0:
        return f"{doc.title} (continued):\n{body}"
    return body


def chunk_document(
    doc: SourceDocument,
    count_tokens: TokenCounter,
    config: ChunkingConfig | None = None,
) -> list[Chunk]:
    config = config or ChunkingConfig()
    text = doc.text.strip()
    if not text:
        return []

    if len(text) <= config.chunk_size and count_tokens(_render(doc, text, 0)) <= config.max_tokens:
        bodies = [text]
    else:
        units = _split_units(text)
        budget = config.chunk_size
        while True:
            overlap = min(config.chunk_overlap, budget // 3)
            bodies = _pack(units, budget, overlap)
            if all(count_tokens(_render(doc, b, i)) <= config.max_tokens for i, b in enumerate(bodies)):
                break
            budget = int(budget * 0.85)
            if budget < 80:
                raise ChunkTooLongError(
                    f"{doc.doc_id}: cannot fit chunks within {config.max_tokens} tokens"
                )

    total = len(bodies)
    chunks = []
    for index, body in enumerate(bodies):
        chunk_text = _render(doc, body, index)
        tokens = count_tokens(chunk_text)  # final guard; packing already enforced this
        if tokens > config.max_tokens:
            raise ChunkTooLongError(f"{doc.doc_id}#{index}: {tokens} tokens > {config.max_tokens}")
        chunk_id = f"{doc.doc_id}#c{index}"
        content_hash = hashlib.sha256(
            (chunk_text + "\x1f" + repr(sorted(doc.metadata.items()))).encode("utf-8")
        ).hexdigest()[:16]
        metadata = {
            **doc.metadata,
            "doc_id": doc.doc_id,
            "parent_doc_id": doc.doc_id,
            "doc_type": doc.doc_type,
            "title": doc.title,
            "chunk_index": index,
            "chunk_count": total,
            "token_count": tokens,
            "content_hash": content_hash,
        }
        chunks.append(Chunk(
            chunk_id=chunk_id,
            parent_doc_id=doc.doc_id,
            chunk_index=index,
            chunk_count=total,
            text=chunk_text,
            token_count=tokens,
            metadata=metadata,
        ))
    return chunks


def chunk_documents(
    docs: list[SourceDocument],
    count_tokens: TokenCounter,
    config: ChunkingConfig | None = None,
) -> list[Chunk]:
    config = config or ChunkingConfig()
    chunks: list[Chunk] = []
    for doc in docs:
        chunks.extend(chunk_document(doc, count_tokens, config))
    return chunks
