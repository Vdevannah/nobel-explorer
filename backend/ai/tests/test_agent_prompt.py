"""Prompt v4 (2026-11-26.4): configuration checks and scripted scenarios.

The scripted model only proves that the rule reaches the model on every call and
that the agent loop handles an invalid category without substituting another
query. It does NOT show that a real model follows the instruction; that needs
a separate, approved real-model run.
"""

import re

import pytest

from backend.ai.agent.prompts import PROMPT_VERSION, SYSTEM_PROMPT

NO_SUBSTITUTION_RULE = (
    "When a question contains an invalid category or a false premise, correct it directly. Do not silently "
    "substitute a different category, person, year or question. Offer alternatives only when the user asks for them "
    "or they are clearly necessary, and label them as alternatives."
)


def test_prompt_version_follows_date_and_counter_convention():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}\.\d+", PROMPT_VERSION)
    assert PROMPT_VERSION == "2026-11-26.4"


def test_no_substitution_rule_is_present_verbatim():
    assert NO_SUBSTITUTION_RULE in SYSTEM_PROMPT


def test_rule_is_general_not_question_specific():
    for specific in ("Mathematics", "1950", "Physics", "Powell", "Einstein", "relativity"):
        assert specific not in NO_SUBSTITUTION_RULE


def test_argument_fixes_must_not_change_the_question():
    assert "fix the arguments once without changing what the user asked about" in SYSTEM_PROMPT
    assert "to correct the arguments once or" not in SYSTEM_PROMPT  # v3 wording removed


@pytest.mark.parametrize("rule", [
    # Evidence attribution, abstention and missing-data behaviour from v3 are preserved.
    "Cite only ids that appear in tool results",
    "Corrections of false premises need evidence too",
    "not as an independent or verified external source",
    "If the evidence is missing or insufficient, say so explicitly",
    "do not fill gaps from general knowledge",
    "ordinary sentences, without citations",
    "Combine tools for multi-part questions",
    "You only have the four tools above",
])
def test_existing_rules_preserved(rule):
    assert rule in SYSTEM_PROMPT


def test_prompt_still_names_exactly_the_four_tools():
    for tool in ("search_laureates", "get_laureate_details", "get_nobel_statistics", "search_nobel_knowledge"):
        assert f"- {tool}:" in SYSTEM_PROMPT


# ---------------------------------------------------------------- scripted scenarios (real agent loop)

langchain = pytest.importorskip("langchain")
pytest.importorskip("chromadb")

from langchain_core.messages import SystemMessage, ToolMessage  # noqa: E402

from backend.ai.agent.config import AgentConfig  # noqa: E402
from backend.ai.agent.service import run_agent_sync  # noqa: E402
from backend.ai.agent.testing import ScriptedChatModel, ai_text, ai_tools, tool_call  # noqa: E402


def _run(question, policy, context):
    cfg = AgentConfig.model_construct(**{**AgentConfig().model_dump(), "openai_api_key": None})
    model = ScriptedChatModel(policy=policy)
    return run_agent_sync(question, config=cfg, chat_model=model, tool_context=context), model


def test_v4_prompt_is_sent_to_the_model_on_every_call(tool_context):
    seen = []

    def policy(messages, n):
        seen.append(next(m.content for m in messages if isinstance(m, SystemMessage)))
        if n == 0:
            return ai_tools(tool_call("search_laureates", {"year": 2022, "category": "Chemistry"}, "c1"))
        return ai_text("Carolyn R. Bertozzi [E1].")

    response, _ = _run("Who won the 2022 Chemistry prize?", policy, tool_context)
    assert response.status == "completed" and len(seen) == 2
    assert all(NO_SUBSTITUTION_RULE in prompt for prompt in seen)


def test_invalid_category_is_corrected_without_a_substituted_query(tool_context):
    """Scripted behaviour that follows the rule: one rejected call, a direct correction, no new query."""
    def policy(messages, n):
        if n == 0:
            return ai_tools(tool_call("search_laureates", {"year": 1950, "category": "Mathematics"}, "c1"))
        error = next(m for m in messages if isinstance(m, ToolMessage))
        assert '"ok": false' in error.content and "not a Nobel Prize category" in error.content
        return ai_text("There is no Nobel Prize in Mathematics, so nobody won one in 1950.")

    response, model = _run("Who won the Nobel Prize in Mathematics in 1950?", policy, tool_context)
    assert response.status == "completed"
    assert [(c.name, c.ok, c.error_type) for c in response.tool_calls] == [("search_laureates", False, "validation_error")]
    assert response.citations == [] and response.grounding == "no_evidence"
    assert model.calls == 2  # no second, substituted search


def test_substituted_answer_is_still_mechanically_accepted(tool_context):
    """Documents the limit of deterministic checks: a substitution like the real P4-R05 answer passes
    citation validation, because the cited evidence is real. Only the prompt (and manual review) guard it."""
    def policy(messages, n):
        if n == 0:
            return ai_tools(tool_call("search_laureates", {"year": 1921, "category": "Physics"}, "c1"))
        return ai_text("There is no Nobel Prize in Mathematics. The 1921 Physics prize went to Albert Einstein [E1].")

    response, _ = _run("Who won the Nobel Prize in Mathematics in 1921?", policy, tool_context)
    assert response.grounding == "cited" and [c.evidence_id for c in response.citations] == ["E1"]
