"""Dependency injection for the tools: where sessions and the index come from.

Production uses the Phase 1 ``read_only_session`` (MySQL ``READ ONLY``
transactions on an unpooled engine) and the persistent Chroma index. Tests
pass an isolated SQLite session factory and a temporary store.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from backend.ai.config import IndexConfig

SessionFactory = Callable[[], AbstractContextManager[Session]]


class IndexUnavailableError(RuntimeError):
    """The vector index has not been built (or cannot be opened)."""


def _default_session_factory() -> AbstractContextManager[Session]:
    from backend.ai.documents import read_only_session

    return read_only_session()


def default_store_provider(index_config: IndexConfig | None = None):
    """Return the process-wide store, refusing to create an index on read.

    ``NobelVectorStore`` creates an empty collection when none exists, which
    is right for the index builder but wrong for a query tool: a missing
    index must be reported, not silently replaced by an empty one.
    """
    config = index_config or IndexConfig()
    if not config.persist_dir.exists():
        raise IndexUnavailableError(
            "The knowledge index has not been built. Run: python -m backend.ai.build_index"
        )
    if index_config is None:
        from backend.ai.retrieval import get_default_store

        store = get_default_store()  # cached process-wide store for the default index
    else:
        # A non-default index must be queried through its own configuration,
        # not the cached default store (which points at the default directory).
        from backend.ai.embeddings import SentenceTransformerEmbedder
        from backend.ai.vector_store import NobelVectorStore

        store = NobelVectorStore(SentenceTransformerEmbedder(), config)
    if store.config.collection_name not in [
        c if isinstance(c, str) else c.name for c in store.client.list_collections()
    ]:
        raise IndexUnavailableError(
            "The knowledge collection does not exist. Run: python -m backend.ai.build_index"
        )
    return store


@dataclass(frozen=True)
class ToolContext:
    session_factory: SessionFactory = field(default=_default_session_factory)
    store_provider: Callable[[], Any] = field(default=default_store_provider)
