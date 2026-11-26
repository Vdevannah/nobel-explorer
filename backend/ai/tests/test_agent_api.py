"""POST /ai/chat: validation, availability, status codes and dependency injection."""

from importlib.util import find_spec

import pytest
from fastapi.testclient import TestClient

from backend.ai.agent.config import AgentConfig
from backend.main import app
from backend.routes import ai as ai_route

SECRET = "sk-test-API-NEVER-LEAK-42"
QUESTION = {"question": "Who won the 2022 Nobel Prize in Chemistry?"}

# Tests that run the real agent need LangChain and ChromaDB; skip (not error) without them.
requires_ai = pytest.mark.skipif(not (find_spec("langchain") and find_spec("chromadb")),
                                 reason="AI packages (.venv-ai) not installed")


@pytest.fixture()
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def _enable(config: AgentConfig | None = None):
    app.dependency_overrides[ai_route.get_agent_config] = lambda: config or AgentConfig(enabled=True, openai_api_key=SECRET)


def _runner(fn):
    app.dependency_overrides[ai_route.get_agent_runner] = lambda: fn


# ---------------------------------------------------------------- no AI packages needed

def test_disabled_by_default_returns_503_without_running(client, monkeypatch):
    monkeypatch.delenv("AI_AGENT_ENABLED", raising=False)
    _runner(lambda *a: pytest.fail("runner must not be called"))
    response = client.post("/ai/chat", json=QUESTION)
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable" and "disabled" in body["error"]["message"] and body["request_id"]


def test_missing_api_key_returns_503(client):
    _enable(AgentConfig(enabled=True))
    _runner(lambda *a: pytest.fail("runner must not be called"))
    response = client.post("/ai/chat", json=QUESTION)
    assert response.status_code == 503 and "OPENAI_API_KEY" in response.json()["error"]["message"]


def test_invalid_configuration_returns_503(client, monkeypatch):
    monkeypatch.setenv("AI_AGENT_MAX_TOOL_CALLS", "999")
    monkeypatch.setenv("OPENAI_API_KEY", SECRET)
    response = client.post("/ai/chat", json=QUESTION)
    assert response.status_code == 503 and SECRET not in response.text


@pytest.mark.parametrize("payload", [{}, {"question": ""}, {"question": "   "}, {"question": 42},
                                     {"question": "x" * 4001}, {"question": "ok", "admin": True}])
def test_request_validation(client, payload):
    _enable()
    _runner(lambda *a: pytest.fail("runner must not be called"))
    assert client.post("/ai/chat", json=payload).status_code == 422


def test_configured_question_limit_enforced_before_agent(client):
    _enable(AgentConfig(enabled=True, openai_api_key=SECRET, max_question_chars=50))
    _runner(lambda *a: pytest.fail("runner must not be called"))
    response = client.post("/ai/chat", json={"question": "x" * 51})
    assert response.status_code == 422 and "50" in response.json()["detail"]


def test_missing_ai_packages_reported_as_unavailable(client):
    async def missing(*args):
        raise ImportError("No module named 'langchain'")

    _enable()
    _runner(missing)
    response = client.post("/ai/chat", json=QUESTION)
    assert response.status_code == 503 and "not installed" in response.json()["error"]["message"]


def test_existing_routes_unaffected(client):
    assert client.get("/").status_code == 200
    assert client.get("/openapi.json").json()["paths"]["/ai/chat"]["post"]


# ---------------------------------------------------------------- with the real agent and a fake model

@pytest.fixture()
def fake_agent_runner(tool_context):
    pytest.importorskip("langchain")
    from backend.ai.agent.service import run_agent
    from backend.ai.agent.testing import ScriptedChatModel, planned_policy

    def make(steps, **kwargs):
        async def runner(question, config, request_id):
            model = ScriptedChatModel(policy=planned_policy(steps, **kwargs))
            return await run_agent(question, config=config, chat_model=model, tool_context=tool_context,
                                   request_id=request_id)
        return runner

    return make


@requires_ai
def test_successful_chat_response(client, fake_agent_runner):
    _enable()
    _runner(fake_agent_runner([[{"tool": "search_laureates", "args": {"year": 2022, "category": "Chemistry"}}]]))
    response = client.post("/ai/chat", json=QUESTION)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed" and body["grounding"] == "cited"
    assert set(body) == {"request_id", "status", "answer", "grounding", "citations", "tool_calls",
                         "evidence_limitations", "model", "model_calls", "usage", "latency_ms", "error"}
    assert body["tool_calls"][0]["name"] == "search_laureates" and len(body["citations"]) == 3
    assert "data" not in body["tool_calls"][0]  # raw tool outputs are never exposed
    assert SECRET not in response.text


@requires_ai
def test_provider_error_maps_to_502(client, tool_context):
    pytest.importorskip("langchain")
    import httpx2
    import openai

    from backend.ai.agent.service import run_agent
    from backend.ai.agent.testing import ScriptedChatModel, script

    async def runner(question, config, request_id):
        exc = openai.APITimeoutError(request=httpx2.Request("POST", "https://api.openai.com"))
        return await run_agent(question, config=config, chat_model=ScriptedChatModel(policy=script(exc)),
                               tool_context=tool_context, request_id=request_id)

    _enable()
    _runner(runner)
    response = client.post("/ai/chat", json=QUESTION)
    assert response.status_code == 502 and response.json()["error"]["type"] == "provider_timeout"


@requires_ai
def test_budget_exhaustion_is_a_controlled_200(client, tool_context):
    pytest.importorskip("langchain")
    from backend.ai.agent.service import run_agent
    from backend.ai.agent.testing import ScriptedChatModel, ai_tools, tool_call

    async def runner(question, config, request_id):
        looping = ScriptedChatModel(policy=lambda m, n: ai_tools(
            tool_call("get_nobel_statistics", {"operation": "summary"}, f"l{n}")))
        return await run_agent(question, config=config, chat_model=looping, tool_context=tool_context,
                               request_id=request_id)

    _enable(AgentConfig(enabled=True, openai_api_key=SECRET, max_model_calls=2))
    _runner(runner)
    response = client.post("/ai/chat", json=QUESTION)
    assert response.status_code == 200 and response.json()["status"] == "budget_exhausted"
