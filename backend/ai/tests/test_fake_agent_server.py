"""Development-only fake agent server: real endpoint and agent, scripted model only."""

from __future__ import annotations

import pytest

pytest.importorskip("langchain")

from fastapi.testclient import TestClient  # noqa: E402

import backend.ai.agent.service as service  # noqa: E402
from backend.ai.evaluation import fake_agent_server as fake  # noqa: E402
from backend.main import app  # noqa: E402


@pytest.fixture()
def client(tool_context, monkeypatch):
    # create_dev_app patches process globals; register them so monkeypatch restores them.
    monkeypatch.setattr(service, "build_chat_model", service.build_chat_model)
    monkeypatch.setenv("OPENAI_API_KEY", "placeholder-not-a-real-key")
    fake.create_dev_app(tool_context=tool_context)
    yield TestClient(app)
    app.dependency_overrides.clear()


def ask(client, question):
    return client.post("/ai/chat", json={"question": question})


def test_supported_question_runs_real_agent_and_tools_with_scripted_model(client):
    response = ask(client, "Who won the 2022 Chemistry prize?")  # UI wording, alias of R01
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["model"] == fake.SCRIPTED_MODEL_NAME
    assert [call["name"] for call in body["tool_calls"]] == ["search_laureates"]
    assert body["tool_calls"][0]["ok"] is True
    titles = {c["title"] for c in body["citations"]}
    assert titles == {"Carolyn R. Bertozzi", "K. Barry Sharpless", "Morten Meldal"}
    assert {c["citation_status"] for c in body["citations"]} == {"structured_record"}
    assert body["grounding"] == "cited"
    assert body["usage"] is None or body["usage"]["total_tokens"] == 0


def test_unsupported_question_fails_closed_without_any_provider(client):
    response = ask(client, "What is the airspeed velocity of an unladen swallow?")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["answer"] is None
    assert "scripted" in body["error"]["message"]
    assert body["model_calls"] == 0 and body["tool_calls"] == []


def test_real_provider_construction_is_refused(client):
    with pytest.raises(RuntimeError, match="never constructs a real language-model client"):
        service.build_chat_model(fake.scripted_config())


def test_openai_key_is_removed_from_the_process(client):
    import os

    assert "OPENAI_API_KEY" not in os.environ


def test_freshness_question_reports_coverage_without_fabricating(client):
    response = ask(client, "Who won the 2026 Chemistry prize?")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["citations"] == []
    assert body["grounding"] == "no_evidence"
    call = body["tool_calls"][0]
    assert (call["name"], call["ok"], call["arguments"]["year"], call["evidence_ids"]) == ("search_laureates", True, 2026, [])
    answer = body["answer"]
    assert "No matching laureates were found" in answer
    assert "does not mean the prize was not awarded" in answer
    assert "covers prizes awarded" in answer  # coverage computed from the database by the tool
    assert not any(name in answer for name in ("Bertozzi", "Sharpless", "Meldal", "Curie"))


def test_existing_routes_still_served(client):
    assert client.get("/").json() == {"message": "Nobel Explorer API is running"}


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.10", "example.org", "::"])
def test_non_loopback_hosts_are_refused(host):
    with pytest.raises(SystemExit):
        fake.require_loopback(host)


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost"])
def test_loopback_hosts_are_allowed(host):
    assert fake.require_loopback(host) == host


def test_plans_cover_ui_questions_and_dataset():
    plans = fake.load_plans()
    for question in [
        "Who won the 2022 Chemistry prize?",
        "Explain click chemistry in simple terms.",
        "Who won the 2023 Medicine prize and what did they discover?",
        "How do solar cells convert sunlight into electricity?",
        "Which three birth countries have the most Nobel laureates?",
        "Why did Albert Einstein receive the Nobel Prize?",
        "Who won the Nobel Prize in Mathematics in 1950?",
        "Explain sourdough fermentation.",
        "Who won the 2026 Chemistry prize?",
    ]:
        assert fake.normalise_question(question) in plans, question
    assert plans[fake.normalise_question("Who won the 2026 Chemistry prize?")]["freshness"] is True


def test_production_app_does_not_import_the_fake_server():
    import subprocess
    import sys

    code = ("import sys, backend.main; "
            "print('backend.ai.evaluation.fake_agent_server' in sys.modules, "
            "bool(backend.main.app.dependency_overrides))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout.split()
    assert out == ["False", "False"]
