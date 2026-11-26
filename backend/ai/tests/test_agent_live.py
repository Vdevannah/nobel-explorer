"""Opt-in agent integration tests.

live_db  : fake model + real tools against the live read-only MySQL database and real index
           (AI_RUN_LIVE_DB_TESTS=1 AI_RUN_REAL_MODEL_TESTS=1).
paid_llm : real OpenAI model. NEVER run without explicit approval (AI_RUN_PAID_LLM_TESTS=1).
"""

import pytest

pytest.importorskip("langchain")


@pytest.mark.live_db
@pytest.mark.real_model
def test_live_agent_answers_2022_chemistry_with_fake_model():
    from backend.ai.agent.config import AgentConfig
    from backend.ai.agent.service import run_agent_sync
    from backend.ai.agent.testing import ScriptedChatModel, planned_policy

    model = ScriptedChatModel(policy=planned_policy(
        [[{"tool": "search_laureates", "args": {"year": 2022, "category": "Chemistry"}}]]))
    response = run_agent_sync("Who won the 2022 Nobel Prize in Chemistry?", config=AgentConfig(), chat_model=model)
    assert response.status == "completed" and response.grounding == "cited"
    for name in ("Carolyn R. Bertozzi", "K. Barry Sharpless", "Morten Meldal"):
        assert name in response.answer


@pytest.mark.live_db
@pytest.mark.real_model
def test_live_fake_evaluation_and_negative_controls():
    import asyncio

    from backend.ai.evaluation.run_agent_eval import evaluate

    report = asyncio.run(evaluate("fake"))
    assert report["summary"]["tool_selection"]["rate"] == 1.0
    assert report["summary"]["citation_validity"]["rate"] == 1.0
    assert all(control["detected"] for control in report["negative_controls"])


@pytest.mark.paid_llm
def test_paid_smoke_question():  # pragma: no cover - requires approval and credentials
    from backend.ai.agent.config import load_agent_config
    from backend.ai.agent.service import run_agent_sync

    config = load_agent_config()
    assert config.availability()[0], "agent must be enabled and configured"
    response = run_agent_sync("Who won the 2022 Nobel Prize in Chemistry?", config=config)
    assert response.status == "completed" and "Bertozzi" in (response.answer or "")
