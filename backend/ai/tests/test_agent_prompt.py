"""Prompt configuration checks and scripted scenarios (v4 rule from 2026-11-26.4; style rules from 2026-11-27.1).

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
    assert PROMPT_VERSION == "2026-11-27.3"


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
    "If the tools have no record, say so explicitly",
    "never supply such facts from memory",
    "ordinary sentences, without citations",
    "Combine tools for multi-part questions",
    "You only have the four tools above",
])
def test_existing_rules_preserved(rule):
    assert rule in SYSTEM_PROMPT


def test_style_rules_ask_for_direct_answers_without_meta_introductions():
    assert "Begin directly with the scientific explanation or the factual answer." in SYSTEM_PROMPT
    assert "do not add verification disclaimers about it" in SYSTEM_PROMPT
    # Old wording that produced "Nobel Explorer educational material describes ..." openings is gone.
    assert "describe it as Nobel Explorer educational material" not in SYSTEM_PROMPT


def test_educational_content_is_still_not_presented_as_verified():
    assert "Treat it as Nobel Explorer educational content" in SYSTEM_PROMPT
    assert "never present its related_source as a citation" in SYSTEM_PROMPT


def test_warnings_for_missing_or_conflicting_evidence_remain():
    assert "Mention a limitation only when it is genuinely necessary" in SYSTEM_PROMPT
    assert "If the tools have no record, say so explicitly in one short sentence" in SYSTEM_PROMPT


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


# ---------------------------------------------------------------- general-knowledge fallback (2026-11-27.2)

def test_general_knowledge_fallback_is_bounded():
    assert "Use retrieved evidence first." in SYSTEM_PROMPT
    assert "never cite unrelated search results" in SYSTEM_PROMPT
    assert "you may give a concise explanation from well-established general scientific knowledge" in SYSTEM_PROMPT
    assert "Do not cite it, do not attribute it to Nobel Explorer or to any named source" in SYSTEM_PROMPT
    assert "do not explain database limitations" in SYSTEM_PROMPT
    assert "put the general explanation in a separate final paragraph without citations" in SYSTEM_PROMPT


def test_nobel_specific_facts_still_come_only_from_tools():
    assert "Specific Nobel facts (who won, years, categories, motivations, affiliations, counts and other statistics)" in SYSTEM_PROMPT
    assert "come only from tool results" in SYSTEM_PROMPT
    assert "do not fill gaps from general knowledge" not in SYSTEM_PROMPT  # replaced by the bounded fallback


def test_abstention_is_preserved_for_unrelated_time_sensitive_or_uncertain_questions():
    assert "Decline briefly, in one sentence, when a question is unrelated to Nobel Prizes" in SYSTEM_PROMPT
    assert "when it depends on recent or current events, or when you are not confident" in SYSTEM_PROMPT
    assert "Never invent facts, names, numbers, URLs or citations." in SYSTEM_PROMPT


# ---------------------------------------------------------------- answer style (2026-11-27.3)

@pytest.mark.parametrize("phrase", [
    "The search returned material about...", "The retrieved evidence...", "Nobel Explorer has no explanation...",
])
def test_retrieval_commentary_openings_are_named_as_forbidden(phrase):
    assert phrase in SYSTEM_PROMPT
    assert "Never open with commentary about the search" in SYSTEM_PROMPT


def test_no_retrieval_or_coverage_discussion_in_ordinary_explanations():
    assert ("Do not discuss search results, retrieval failures, weak matches or database coverage in ordinary "
            "scientific explanations.") in SYSTEM_PROMPT
    assert "The interface already shows how the answer was found" in SYSTEM_PROMPT
    assert "say that it does not" not in SYSTEM_PROMPT  # wording that invited retrieval commentary


def test_readable_formatting_and_unicode_math():
    assert 'simple bullet lists (lines starting with "- ")' in SYSTEM_PROMPT
    assert "Do not use Markdown headings, tables or links." in SYSTEM_PROMPT
    assert "E = mc²" in SYSTEM_PROMPT and "not LaTeX" in SYSTEM_PROMPT
    assert "Apply these rules to every scientific topic." in SYSTEM_PROMPT


def test_accuracy_rules_are_unchanged_by_the_style_rules():
    for rule in ("Cite only ids that appear in tool results", "Never invent facts, names, numbers, URLs or citations.",
                 "Corrections of false premises need evidence too", "If the tools have no record, say so explicitly"):
        assert rule in SYSTEM_PROMPT
