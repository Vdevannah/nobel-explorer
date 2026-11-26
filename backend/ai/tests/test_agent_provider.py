"""The REAL ChatOpenAI client and OpenAI SDK with a MOCKED HTTP transport.

Nothing leaves the machine: httpx2.MockTransport answers every request. These
tests pin the request the production model factory builds for gpt-6-luna and
check SDK retries and error mapping end to end through the agent.
"""

import json

import pytest

pytest.importorskip("langchain_openai")
pytest.importorskip("chromadb")

import httpx2  # noqa: E402

from backend.ai.agent.config import AgentConfig  # noqa: E402
from backend.ai.agent.prompts import SYSTEM_PROMPT  # noqa: E402
from backend.ai.agent.service import build_chat_model, run_agent_sync  # noqa: E402
from backend.ai.tools.registry import TOOL_NAMES  # noqa: E402

MOCK_KEY = "sk-mock-transport-NOT-REAL-000"


def _completion(message: dict, usage=(2500, 30)) -> dict:
    return {"id": "chatcmpl-mock", "object": "chat.completion", "created": 0, "model": "gpt-6-luna",
            "choices": [{"index": 0, "finish_reason": "tool_calls" if message.get("tool_calls") else "stop",
                         "message": {"role": "assistant", **message}}],
            "usage": {"prompt_tokens": usage[0], "completion_tokens": usage[1], "total_tokens": sum(usage)}}


TOOL_TURN = _completion({"content": None, "tool_calls": [{
    "id": "call_1", "type": "function",
    "function": {"name": "search_laureates", "arguments": json.dumps({"year": 2022, "category": "Chemistry"})}}]})
ANSWER_TURN = _completion({"content": "Carolyn R. Bertozzi [E1], K. Barry Sharpless [E2] and Morten Meldal [E3]."},
                          usage=(3600, 40))


class Provider:
    """Scripted HTTP endpoint; records every request it receives."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests: list[dict] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append({"url": str(request.url), "body": json.loads(request.content or b"{}"),
                              "has_auth": request.headers.get("authorization", "").startswith("Bearer ")})
        status, payload = self.responses[min(len(self.requests) - 1, len(self.responses) - 1)]
        if isinstance(payload, Exception):
            raise payload
        return httpx2.Response(status, json=payload)


def _model(provider: Provider, **overrides):
    config = AgentConfig(enabled=True, openai_api_key=MOCK_KEY, **overrides)
    transport = httpx2.MockTransport(provider)
    model = build_chat_model(config, http_client=httpx2.Client(transport=transport),
                             http_async_client=httpx2.AsyncClient(transport=transport))
    return config, model


def test_request_parameters_for_gpt6_luna(tool_context):
    provider = Provider((200, TOOL_TURN), (200, ANSWER_TURN))
    config, model = _model(provider)
    response = run_agent_sync("Who won the 2022 Nobel Prize in Chemistry?", config=config, chat_model=model,
                              tool_context=tool_context)

    first = provider.requests[0]
    body = first["body"]
    assert first["url"] == "https://api.openai.com/v1/chat/completions"  # not /v1/responses
    assert body["model"] == "gpt-6-luna"
    assert body["reasoning_effort"] == "none"
    assert body["max_completion_tokens"] == 800 and "max_tokens" not in body
    assert "temperature" not in body and "parallel_tool_calls" not in body
    assert sorted(t["function"]["name"] for t in body["tools"]) == sorted(TOOL_NAMES)
    assert body["messages"][0]["content"] == SYSTEM_PROMPT and body["messages"][1]["role"] == "user"
    assert first["has_auth"]

    second = provider.requests[1]["body"]["messages"]
    tool_message = next(m for m in second if m["role"] == "tool")
    assert json.loads(tool_message["content"])["evidence_ids"] == ["E1", "E2", "E3"]

    assert response.status == "completed" and response.grounding == "cited"
    assert response.model_calls == 2 and response.usage.total_tokens == 2530 + 3640
    assert MOCK_KEY not in response.model_dump_json()


def test_optional_parameters_follow_configuration(tool_context):
    provider = Provider((200, ANSWER_TURN))
    config, model = _model(provider, reasoning_effort=None, temperature=0.2)
    run_agent_sync("Hi", config=config, chat_model=model, tool_context=tool_context)
    body = provider.requests[0]["body"]
    assert "reasoning_effort" not in body and body["temperature"] == 0.2


def test_provider_retry_is_one_model_call_but_two_http_attempts(tool_context):
    provider = Provider((500, {"error": {"message": "temporary"}}), (200, ANSWER_TURN))
    config, model = _model(provider)  # provider_max_retries=1
    response = run_agent_sync("Hi", config=config, chat_model=model, tool_context=tool_context)
    assert len(provider.requests) == 2 and response.model_calls == 1 and response.status == "completed"


def test_exhausted_retries_become_a_sanitised_provider_error(tool_context):
    provider = Provider((500, {"error": {"message": f"upstream failure for key {MOCK_KEY}"}}))
    config, model = _model(provider)
    response = run_agent_sync("Hi", config=config, chat_model=model, tool_context=tool_context)
    assert len(provider.requests) == 2  # 1 attempt + 1 retry, then stop
    assert response.status == "error" and response.error.type == "provider_error"
    assert MOCK_KEY not in response.model_dump_json()


def test_authentication_error_from_real_sdk(tool_context):
    body = {"error": {"message": f"Incorrect API key provided: {MOCK_KEY}", "type": "invalid_request_error",
                      "code": "invalid_api_key"}}
    provider = Provider((401, body))
    config, model = _model(provider)
    response = run_agent_sync("Hi", config=config, chat_model=model, tool_context=tool_context)
    assert response.error.type == "provider_auth" and len(provider.requests) == 1  # 401 is not retried
    assert MOCK_KEY not in response.model_dump_json()


def test_transport_timeout_maps_to_provider_timeout(tool_context):
    provider = Provider((0, httpx2.ReadTimeout("read timed out")))
    config, model = _model(provider)
    response = run_agent_sync("Hi", config=config, chat_model=model, tool_context=tool_context)
    assert response.error.type == "provider_timeout" and len(provider.requests) == 2


def test_default_model_is_gpt6_luna_and_chat_completions_is_pinned():
    config = AgentConfig(enabled=True, openai_api_key=MOCK_KEY)
    model = build_chat_model(config)  # construction only; no request is made
    assert config.model == "gpt-6-luna"
    assert model.use_responses_api is False and model.reasoning_effort == "none" and model.max_tokens == 800


def test_model_not_found_is_explicit(tool_context):
    provider = Provider((404, {"error": {"message": "The model `gpt-6-luna` does not exist", "code": "model_not_found"}}))
    config, model = _model(provider)
    response = run_agent_sync("Hi", config=config, chat_model=model, tool_context=tool_context)
    assert response.error.type == "provider_model_not_found" and "OPENAI_MODEL" in response.error.message


def test_rate_limit_is_retried_then_reported(tool_context):
    provider = Provider((429, {"error": {"message": "slow down"}}))
    config, model = _model(provider)
    response = run_agent_sync("Hi", config=config, chat_model=model, tool_context=tool_context)
    assert response.error.type == "provider_rate_limited" and len(provider.requests) == 2
