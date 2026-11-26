"""Error handling, read-only behaviour and credential safety of the tool layer."""

import json
from contextlib import contextmanager

import pytest

pytest.importorskip("langchain_core")
pytest.importorskip("chromadb")

from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

from backend.ai.config import IndexConfig  # noqa: E402
from backend.ai.tools.context import ToolContext, default_store_provider  # noqa: E402
from backend.ai.tools.registry import get_tool_registry  # noqa: E402

SECRET_USER = "nobel_secret_user"
SECRET_HOST = "db.internal.example"


@contextmanager
def _failing_session():
    raise OperationalError(
        "SELECT 1", {}, Exception(1045, f"Access denied for user '{SECRET_USER}'@'{SECRET_HOST}' (using password: YES)")
    )
    yield  # pragma: no cover


def _assert_no_leak(payload):
    dumped = json.dumps(payload)
    for secret in (SECRET_USER, SECRET_HOST, "Traceback", "password", "mysql+pymysql", "/Users/"):
        assert secret not in dumped


@pytest.mark.parametrize("name, args", [
    ("search_laureates", {"year": 2022}),
    ("get_laureate_details", {"laureate_id": 249}),
    ("get_nobel_statistics", {"operation": "summary"}),
])
def test_database_failure_is_reported_without_credentials(tool_store, name, args):
    tools = get_tool_registry(ToolContext(session_factory=_failing_session, store_provider=lambda: tool_store))
    result = tools[name].invoke(args)
    assert result["ok"] is False and result["error"]["type"] == "database_unavailable"
    assert "1045" in result["error"]["message"]
    _assert_no_leak(result)


def test_missing_index_is_reported_and_not_created(tool_session_factory, tmp_path):
    missing = tmp_path / "no_index_here"
    tools = get_tool_registry(ToolContext(session_factory=tool_session_factory,
                                          store_provider=lambda: default_store_provider(IndexConfig(persist_dir=missing))))
    result = tools["search_nobel_knowledge"].invoke({"query": "photons"})
    assert result["ok"] is False and result["error"]["type"] == "index_unavailable"
    assert "build_index" in result["error"]["message"]
    assert not missing.exists()


def test_incompatible_index_is_reported(tool_session_factory, tool_store):
    from backend.ai.embeddings import HashingEmbedder
    from backend.ai.vector_store import NobelVectorStore

    def other_model_store():
        store = NobelVectorStore(HashingEmbedder(model_id="test/other"), tool_store.config)
        store.count()
        return store

    tools = get_tool_registry(ToolContext(session_factory=tool_session_factory, store_provider=other_model_store))
    result = tools["search_nobel_knowledge"].invoke({"query": "photons"})
    assert result["error"]["type"] == "index_incompatible"


def test_vector_store_errors_are_reported(tool_session_factory):
    import chromadb.errors

    class BrokenStore:
        def count(self):
            raise chromadb.errors.InternalError("segment reader failed at /Users/someone/ai_index")

    tools = get_tool_registry(ToolContext(session_factory=tool_session_factory, store_provider=BrokenStore))
    result = tools["search_nobel_knowledge"].invoke({"query": "photons"})
    assert result["error"]["type"] == "index_error"
    _assert_no_leak(result)


def test_unexpected_errors_hide_details(tool_session_factory):
    class ExplodingStore:
        def count(self):
            raise RuntimeError(f"connect to mysql+pymysql://{SECRET_USER}:pw@{SECRET_HOST}/nobel failed")

    tools = get_tool_registry(ToolContext(session_factory=tool_session_factory, store_provider=ExplodingStore))
    result = tools["search_nobel_knowledge"].invoke({"query": "photons"})
    assert result["error"] == {"type": "internal_error", "message": "The tool failed unexpectedly (RuntimeError)."}
    _assert_no_leak(result)


def test_fixture_database_is_read_only_and_tools_still_work(tools, tool_session_factory):
    with tool_session_factory() as db:
        with pytest.raises(Exception, match="readonly|read-only|attempt to write"):
            db.execute(text("UPDATE laureate SET full_name = 'x' WHERE laureate_id = 249"))
    assert tools["search_laureates"].invoke({"name": "Einstein"})["data"]["laureates"][0]["full_name"] == \
        "Albert Einstein"


def test_default_context_uses_phase1_read_only_session():
    from backend.ai.tools import context

    with pytest.MonkeyPatch.context() as mp:
        captured = {}

        @contextmanager
        def fake_read_only_session():
            captured["used"] = True
            yield None

        mp.setattr("backend.ai.documents.read_only_session", fake_read_only_session)
        with context.ToolContext().session_factory():
            pass
    assert captured == {"used": True}


def test_sql_like_input_is_treated_as_data(tools):
    result = tools["search_laureates"].invoke({"name": "Robert'); DROP TABLE laureate; --"})
    assert result["ok"] is True and result["data"]["total_matches"] == 0
    assert tools["search_laureates"].invoke({"name": "Einstein"})["data"]["total_matches"] == 1


def test_outputs_expose_no_image_or_internal_fields(tools):
    dumped = json.dumps(tools["get_laureate_details"].invoke({"laureate_id": 249}))
    for field in ("image_url", "image_attribution", "featured", "content_hash"):
        assert field not in dumped


def test_custom_index_config_is_actually_used(monkeypatch, documents, tmp_path):
    # Regression: default_store_provider(config) checked config.persist_dir but
    # then returned the cached DEFAULT store, silently querying another index.
    from backend.ai import embeddings
    from backend.ai.chunking import chunk_documents
    from backend.ai.vector_store import NobelVectorStore

    monkeypatch.setattr(embeddings, "SentenceTransformerEmbedder", lambda: embeddings.HashingEmbedder())
    config = IndexConfig(persist_dir=tmp_path / "custom_index", collection_name="nobel_knowledge")
    builder = NobelVectorStore(embeddings.HashingEmbedder(), config)
    chunks = chunk_documents(documents, embeddings.HashingEmbedder().count_tokens)
    builder.sync(chunks)

    store = default_store_provider(config)
    assert store.config.persist_dir == config.persist_dir
    assert store.count() == len(chunks)


def test_existing_directory_without_collection_is_unavailable(monkeypatch, tmp_path):
    from backend.ai import embeddings
    from backend.ai.tools.context import IndexUnavailableError

    monkeypatch.setattr(embeddings, "SentenceTransformerEmbedder", lambda: embeddings.HashingEmbedder())
    empty_dir = tmp_path / "empty_index"
    empty_dir.mkdir()
    with pytest.raises(IndexUnavailableError, match="collection does not exist"):
        default_store_provider(IndexConfig(persist_dir=empty_dir, collection_name="nobel_knowledge"))
