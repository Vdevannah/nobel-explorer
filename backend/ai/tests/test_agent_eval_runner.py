"""Agent evaluation dataset and scoring logic (no LLM, no database)."""

import json

import pytest

pytest.importorskip("langchain_core")

from langchain_core.messages import ToolMessage  # noqa: E402

from backend.ai.agent.evidence import CitationCheck  # noqa: E402
from backend.ai.agent.schemas import ChatResponse, Citation, ToolCallSummary  # noqa: E402
from backend.ai.evaluation.run_agent_eval import DATASET, score_case, summarise  # noqa: E402

REQUIRED_QUESTIONS = [
    "Who won the 2022 Nobel Prize in Chemistry?",
    "What did Albert Einstein win the Nobel Prize for?",
    "Explain click chemistry in simple terms.",
    "Who won the 2023 Medicine prize and what did they discover?",
    "Which three birth countries have produced the most Nobel laureates in our database?",
    "Who won the Nobel Prize in Mathematics in 1950?",
    "Explain how solar cells convert sunlight into electricity.",
    "Tell me about Curie.",
    "Explain sourdough fermentation.",
    "Did Einstein win the Nobel Prize for general relativity?",
]
CASE = {"id": "X", "category": "exact_structured", "question": "Who won 2022 Chemistry?",
        "expected_tools_any_of": [["search_laureates"]],
        "argument_constraints": [{"tool": "search_laureates", "arg": "category", "equals": "Chemistry"}],
        "must_include_any": [["Bertozzi"]], "must_not_include": ["Mathematics"],
        "grounding_facts": ["Bertozzi"], "citations": {"min_valid": 1, "required_statuses": ["structured_record"]}}


def _response(answer, tools=(("search_laureates", {"category": "chemistry", "year": 2022}),), citations=1,
              status="completed"):
    return ChatResponse(
        request_id="r", status=status, answer=answer,
        tool_calls=[ToolCallSummary(id=f"t{i}", name=n, arguments=a, ok=True) for i, (n, a) in enumerate(tools)],
        citations=[Citation(evidence_id=f"E{i + 1}", tool="search_laureates", kind="laureate_record", title="x",
                            citation_status="structured_record") for i in range(citations)])


def _capture(evidence="Carolyn R. Bertozzi", fabricated=()):
    return {"messages": [ToolMessage(content=evidence, tool_call_id="t0")],
            "citation_check": CitationCheck("", [], list(fabricated), [], [])}


def test_dataset_contains_required_questions_and_fields():
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    questions = [c["question"] for c in data["cases"]]
    assert all(q in questions for q in REQUIRED_QUESTIONS)
    assert len(data["cases"]) >= 30 and len({c["id"] for c in data["cases"]}) == len(data["cases"])
    categories = {c["category"] for c in data["cases"]}
    assert {"exact_structured", "laureate_details", "statistics", "semantic", "multi_step", "clarification",
            "false_premise", "out_of_scope", "insufficient_evidence"} <= categories
    for case in data["cases"]:
        assert case["expected_tools_any_of"] and case["must_include_any"] and case["fake_plan"]


def test_correct_answer_scores_on_every_metric():
    row = score_case(CASE, _response("Carolyn R. Bertozzi [E1]"), _capture())
    assert row["tool_selection"] and row["argument_correctness"]  # "chemistry" normalised to "Chemistry"
    assert row["citation_validity"] and row["fact_presence"] and row["task_success"]
    assert row["groundedness"] is None and row["evaluator_version"] == 3  # manual review, never automated


def test_wrong_tool_and_arguments_detected():
    row = score_case(CASE, _response("Bertozzi", tools=(("search_nobel_knowledge", {"query": "x"}),)), _capture())
    assert row["tool_selection"] is False and row["argument_correctness"] is False


def test_fabricated_citation_detected():
    row = score_case(CASE, _response("Bertozzi [E1]"), _capture(fabricated=["E9"]))
    assert row["citation_validity"] is False


def test_missing_required_citation_status_detected():
    response = _response("Bertozzi [E1]")
    response.citations[0].citation_status = "unverified_educational"
    assert score_case(CASE, response, _capture())["citation_validity"] is False


def test_fact_absent_from_evidence_detected():
    row = score_case(CASE, _response("Bertozzi [E1]"), _capture(evidence="no names here"))
    assert row["fact_presence"] is False


def test_forbidden_phrase_and_status_fail_task():
    assert score_case(CASE, _response("Bertozzi won Mathematics"), _capture())["task_success"] is False
    assert score_case(CASE, _response("Bertozzi", status="budget_exhausted"), _capture())["task_success"] is False


def test_summary_reports_rates_and_mode_interpretation():
    rows = [score_case(CASE, _response("Carolyn R. Bertozzi [E1]"), _capture())] * 2
    summary = summarise(rows, "fake")
    assert summary["task_success"] == {"passed": 2, "applicable": 2, "rate": 1.0}
    assert "NOT real LLM accuracy" in summary["interpretation"]


def test_paid_mode_refuses_without_explicit_opt_in(monkeypatch):
    import asyncio

    from backend.ai.evaluation.run_agent_eval import evaluate

    monkeypatch.delenv("AI_ALLOW_PAID_EVAL", raising=False)
    with pytest.raises(SystemExit, match="AI_ALLOW_PAID_EVAL"):
        asyncio.run(evaluate("openai", ["R01"]))


def test_paid_stages_and_cost_estimate():
    from backend.ai.agent.schemas import Usage
    from backend.ai.evaluation.run_agent_eval import PRICING, STAGES, estimate_cost_usd, main

    assert STAGES[1] == ["R01", "R04", "R06"] and len(STAGES[1]) + len(STAGES[2]) == 10
    assert PRICING["gpt-6-luna"] == {"input": 0.10, "cached_input": 0.01, "output": 0.50}
    usage = Usage(input_tokens=1_000_000, cached_input_tokens=400_000, output_tokens=100_000, total_tokens=1_100_000)
    assert estimate_cost_usd("gpt-6-luna", usage) == round(0.6 * 0.10 + 0.4 * 0.01 + 0.1 * 0.50, 6)
    assert estimate_cost_usd("unknown-model", usage) is None
    with pytest.raises(SystemExit, match="stage1-reviewed"):
        main(["--mode", "openai", "--stage", "2"])


def test_paid_mode_loads_dotenv_without_overriding_shell(monkeypatch, tmp_path):
    """The runner loads .env with override=False: shell values win; no network call is made."""
    import asyncio

    import backend.ai.evaluation.run_agent_eval as runner

    calls = {}

    def fake_load_dotenv(path, override):
        calls["override"] = override
        calls["path_name"] = path.name

    monkeypatch.setattr("dotenv.load_dotenv", fake_load_dotenv)
    monkeypatch.delenv("AI_ALLOW_PAID_EVAL", raising=False)
    with pytest.raises(SystemExit):
        asyncio.run(runner.evaluate("openai", ["R01"]))
    assert calls == {"override": False, "path_name": ".env"}


def test_paid_mode_stops_after_a_provider_error(monkeypatch):
    import asyncio

    import backend.ai.evaluation.run_agent_eval as runner
    from backend.ai.agent.config import AgentConfig

    monkeypatch.setenv("AI_ALLOW_PAID_EVAL", "1")
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr("backend.ai.agent.config.load_agent_config",
                        lambda: AgentConfig(enabled=True, openai_api_key="sk-test-not-real"))
    seen = []

    async def fake_case(case, config, mode, policy=None):
        seen.append(case["id"])
        return {"id": case["id"], "error": "provider_auth", "estimated_cost_usd": 0.0}

    monkeypatch.setattr(runner, "_run_case", fake_case)
    monkeypatch.setattr(runner, "summarise", lambda rows, mode: {"mode": mode})
    report = asyncio.run(runner.evaluate("openai", ["R01", "R04", "R06"]))
    assert seen == ["R01"] and "provider_auth" in report["summary"]["stopped_early"]


def test_rows_keep_full_answer_and_citation_details():
    long_answer = "Carolyn R. Bertozzi [E1] " + "detail " * 100
    row = score_case(CASE, _response(long_answer), _capture())
    assert row["answer"] == long_answer.strip() or row["answer"] == long_answer
    assert len(row["answer_preview"]) == 240 and len(row["answer"]) > 240
    assert row["citation_details"][0]["evidence_id"] == "E1" and "evidence_limitations" in row


# ---------------------------------------------------------------- Phase 3C instrumentation

def test_execution_record_captures_real_tool_results_and_provenance(tool_context):
    pytest.importorskip("chromadb")
    from backend.ai.agent.config import AgentConfig
    from backend.ai.agent.service import run_agent_sync
    from backend.ai.agent.testing import ScriptedChatModel, planned_policy

    capture = {}
    model = ScriptedChatModel(policy=planned_policy(
        [[{"tool": "search_laureates", "args": {"year": 2022, "category": "Chemistry"}},
          {"tool": "search_nobel_knowledge", "args": {"query": "photons knock electrons out of metal", "level": "Simple"}}]]))
    response = run_agent_sync("Q", config=AgentConfig(), chat_model=model, tool_context=tool_context, capture=capture)
    row = score_case(CASE, response, capture)

    kinds = [step["type"] for step in row["execution_sequence"]]
    assert kinds[0] == "human" and kinds.count("tool") == 2 and kinds[-1] == "ai"
    results = {r["name"]: r["result"] for r in row["tool_results"]}
    assert results["search_laureates"]["ok"] and results["search_laureates"]["evidence_ids"]  # the real envelope
    statuses = {e["citation_status"] for e in row["evidence"]}
    assert {"structured_record", "unverified_educational"} <= statuses
    explanation = next(e for e in row["evidence"] if e["citation_status"] == "unverified_educational")
    assert explanation["source"] is None and explanation["related_source_context_only"]["url"].startswith("https://")
    assert row["tool_call_count"] == 2 and len(row["tool_latency_ms"]) == 2
    assert row["answer"] == response.answer  # complete, untruncated
    json.dumps(row, default=str)  # serialisable


def test_evidence_is_kept_when_the_provider_fails_mid_run(tool_context):
    pytest.importorskip("chromadb")
    import httpx2
    import openai

    from backend.ai.agent.config import AgentConfig
    from backend.ai.agent.service import run_agent_sync
    from backend.ai.agent.testing import ScriptedChatModel, ai_tools, script, tool_call

    timeout = openai.APITimeoutError(request=httpx2.Request("POST", "https://api.openai.com"))
    model = ScriptedChatModel(policy=script(ai_tools(tool_call("search_laureates", {"year": 2022}, "c1")), timeout))
    capture = {}
    response = run_agent_sync("Q", config=AgentConfig(), chat_model=model, tool_context=tool_context, capture=capture)
    row = score_case(CASE, response, capture)
    assert row["error"] == "provider_timeout" and row["evidence"]  # partial evidence preserved


def test_unknown_case_ids_are_rejected():
    import asyncio

    from backend.ai.evaluation.run_agent_eval import evaluate

    with pytest.raises(SystemExit, match="Unknown case id"):
        asyncio.run(evaluate("fake", ["R04", "R99"]))


def test_output_containing_the_api_key_is_never_written(monkeypatch, tmp_path):
    import backend.ai.evaluation.run_agent_eval as runner

    secret = "sk-test-SHOULD-NEVER-BE-WRITTEN"
    monkeypatch.setenv("OPENAI_API_KEY", secret)

    async def fake_evaluate(*args, **kwargs):
        return {"summary": {"mode": "fake", "leak": secret}, "cases": []}

    monkeypatch.setattr(runner, "evaluate", fake_evaluate)
    out = tmp_path / "report.json"
    with pytest.raises(SystemExit, match="API key"):
        runner.main(["--mode", "fake", "--output", str(out)])
    assert not out.exists()



def test_v2_abstention_case_scored_by_abstention_check():
    case = {**CASE, "expect_abstention": True, "must_include_any": [["does not contain"]], "citations": {"allow_none": True}}
    good = score_case(case, _response("Nobel Explorer has no reliable evidence about sourdough.", tools=(), citations=0),
                      _capture())
    assert good["task_success"] and good["abstention"]["valid"]
    bad = score_case(case, _response("No reliable evidence. Sourdough uses wild yeast.", tools=(), citations=0), _capture())
    assert not bad["task_success"] and bad["abstention"]["reason"] == "abstention followed by claims"


def test_v2_concept_coverage_accepts_paraphrase():
    case = {**CASE, "must_include_any": [], "grounding_facts": [],
            "concepts": [["photovoltaic", "solar cell", "semiconductor"], ["photon", "light"]]}
    row = score_case(case, _response("Solar cells turn light into current [E1]"), _capture())
    assert row["concept_coverage"]["covered"] and row["task_success"]
