"""Agent evaluation (Phase 3).

    python -m backend.ai.evaluation.run_agent_eval --mode fake   [--output PATH]
    python -m backend.ai.evaluation.run_agent_eval --mode openai --stage 1 [--max-cost-usd 0.25]   # PAID, opt-in
    python -m backend.ai.evaluation.run_agent_eval --mode openai --stage 2 --stage1-reviewed       # PAID, opt-in

Paid stages: stage 1 = R01, R04, R06 (3 representative questions); stage 2 = the
remaining 7 required questions and requires --stage1-reviewed. A cumulative
cost cap stops the run before the next question once it is reached.

Modes
-----
fake    The deterministic ScriptedChatModel follows each case's ``fake_plan``
        through the REAL agent loop, tools, database and validation. It checks
        orchestration, evidence handling and this evaluator. It says NOTHING
        about how well a real LLM chooses tools. Negative controls (deliberately
        wrong behaviour) must be detected for the evaluator to be trusted.
openai  Real model via OPENAI_* configuration. Refuses to run unless
        AI_ALLOW_PAID_EVAL=1 is set and the agent is enabled and configured.

Per-case metrics
----------------
tool_selection       set of called tool names is one of ``expected_tools_any_of``
argument_correctness every constraint holds for at least one call of that tool
                     (arguments compared after Pydantic normalisation)
citation_validity    no fabricated ids/URLs, min/max valid citations and the
                     required citation statuses are present
groundedness         every grounding fact appears in the answer AND in tool output
task_success         status completed, every must_include_any group matched and
                     no must_not_include phrase present
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

DATASET = Path(__file__).with_name("agent_eval_set.json")

STAGES = {1: ["R01", "R04", "R06"], 2: ["R02", "R03", "R05", "R07", "R08", "R09", "R10"]}

# USD per 1M tokens, Standard tier, prompts under 272K tokens.
# Source: https://developers.openai.com/api/docs/models/gpt-6-luna (checked 2026-11-26).
PRICING = {"gpt-6-luna": {"input": 0.10, "cached_input": 0.01, "output": 0.50}}


def estimate_cost_usd(model: str, usage) -> float | None:
    rates = PRICING.get(model)
    if rates is None or usage is None:
        return None
    cached = min(usage.cached_input_tokens, usage.input_tokens)
    return round(((usage.input_tokens - cached) * rates["input"] + cached * rates["cached_input"]
                  + usage.output_tokens * rates["output"]) / 1_000_000, 6)


def _normalise_args(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    from backend.ai.tools.langchain_tools import _SCHEMAS

    try:
        return _SCHEMAS[tool].model_validate(args).model_dump()
    except Exception:  # noqa: BLE001 - invalid or unknown: compare raw values
        return dict(args)


def _contains(text: str, phrase: str) -> bool:
    return phrase.lower() in text.lower()


def _parse(content: Any) -> Any:
    try:
        return json.loads(content)
    except (TypeError, ValueError):
        return str(content)


def execution_record(capture: dict[str, Any]) -> dict[str, Any]:
    """What actually happened in this run: messages, raw tool results and evidence."""
    sequence, tool_results = [], []
    for message in capture.get("messages", []):
        if isinstance(message, HumanMessage):
            sequence.append({"type": "human", "content": message.content})
        elif isinstance(message, AIMessage):
            sequence.append({"type": "ai", "content": message.content,
                             "tool_calls": [{"id": c["id"], "name": c["name"], "args": c["args"]}
                                            for c in message.tool_calls or []],
                             "usage": message.usage_metadata})
        elif isinstance(message, ToolMessage):
            result = _parse(message.content)
            ids = result.get("evidence_ids", []) if isinstance(result, dict) else []
            sequence.append({"type": "tool", "name": message.name, "tool_call_id": message.tool_call_id,
                             "status": message.status, "evidence_ids": ids})
            tool_results.append({"tool_call_id": message.tool_call_id, "name": message.name,
                                 "status": message.status, "result": result})
    registry = capture.get("registry")
    evidence = []
    if registry is not None:
        for item in registry.items.values():
            evidence.append({"evidence_id": item.evidence_id, "tool": item.tool, "kind": item.kind,
                             "title": item.title, "citation_status": item.citation_status,
                             "source": item.source, "source_name": item.source_name,
                             "related_source_context_only": item.related_source, "reference": item.reference})
    return {"execution_sequence": sequence, "tool_results": tool_results, "evidence": evidence}


EVALUATOR_VERSION = 2


def score_core(case: dict[str, Any], *, answer: str, status: str, calls: list[tuple[str, dict[str, Any]]],
               citation_statuses: list[str], citations_tampered: bool | None,
               tool_results: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Evaluator v2, shared by live runs and offline re-evaluation of saved records.

    ``groundedness`` is intentionally None: claim-level grounding cannot be
    established automatically, so it is assessed manually (``support_review``
    lists what a reviewer should check). ``fact_presence`` is the v1 keyword
    check (formerly reported as "groundedness").
    """
    from backend.ai.evaluation.grounding import (
        abstention_check, citation_support_review, concept_coverage, evidence_texts)

    called = {name for name, _ in calls}
    expected_sets = [set(x) for x in case.get("expected_tools_any_of", [])]
    tool_selection = called in expected_sets if expected_sets else None

    constraints = case.get("argument_constraints", [])
    arg_results = []
    for constraint in constraints:
        candidates = [_normalise_args(name, args) for name, args in calls if name == constraint["tool"]]
        if "equals" in constraint:
            arg_results.append(any(a.get(constraint["arg"]) == constraint["equals"] for a in candidates))
        else:
            arg_results.append(any(a.get(constraint["arg"]) in constraint["one_of"] for a in candidates))
    argument_correctness = all(arg_results) if constraints else None

    requirements = case.get("citations", {})
    citation_validity = bool(
        status == "completed"
        and not citations_tampered
        and (requirements.get("allow_none") or len(citation_statuses) >= requirements.get("min_valid", 1))
        and len(citation_statuses) <= requirements.get("max_valid", 10**6)
        and set(requirements.get("required_statuses", [])) <= set(citation_statuses)
    )

    texts = evidence_texts(tool_results or [])
    evidence_text = " ".join(texts.values()) + " " + json.dumps(tool_results or [], ensure_ascii=False, default=str)
    facts = case.get("grounding_facts", [])
    fact_presence = (all(_contains(answer, f) and _contains(evidence_text, f) for f in facts)
                     if facts and tool_results is not None else None)
    coverage = concept_coverage(answer, case["concepts"]) if case.get("concepts") else None
    abstention = abstention_check(answer, len(citation_statuses)) if case.get("expect_abstention") else None
    review = citation_support_review(answer, texts) if tool_results is not None else None

    if abstention is not None:
        task_success = status == "completed" and abstention["valid"]
    else:
        groups_ok = all(any(_contains(answer, p) for p in group) for group in case.get("must_include_any", []))
        forbidden_ok = not any(_contains(answer, p) for p in case.get("must_not_include", []))
        task_success = status == "completed" and groups_ok and forbidden_ok
        if coverage is not None:
            task_success = task_success and coverage["covered"]

    return {
        "evaluator_version": EVALUATOR_VERSION,
        "tool_selection": tool_selection, "argument_correctness": argument_correctness,
        "citation_validity": citation_validity, "fact_presence": fact_presence,
        "concept_coverage": coverage, "abstention": abstention, "support_review": review,
        "support_review_flagged": review["flagged"] if review else None,
        "groundedness": None,  # manual evidence review required (see support_review)
        "task_success": task_success,
    }


def score_case(case: dict[str, Any], response, capture: dict[str, Any]) -> dict[str, Any]:
    answer = response.answer or ""
    calls = response.tool_calls
    check = capture.get("citation_check")
    record = execution_record(capture)
    tampered = None if check is None else bool(
        check.fabricated_ids or check.removed_urls or check.related_source_urls_removed)
    metrics = score_core(case, answer=answer, status=response.status,
                         calls=[(c.name, c.arguments) for c in calls],
                         citation_statuses=[c.citation_status for c in response.citations],
                         citations_tampered=tampered, tool_results=record["tool_results"])

    return {
        "id": case["id"], "category": case["category"], "question": case["question"],
        "status": response.status, "tools_called": [c.name for c in calls],
        **metrics,
        "grounding": response.grounding, "citations": len(response.citations),
        "model_calls": response.model_calls, "latency_ms": response.latency_ms,
        "total_tokens": response.usage.total_tokens if response.usage else None,
        "input_tokens": response.usage.input_tokens if response.usage else None,
        "cached_input_tokens": response.usage.cached_input_tokens if response.usage else None,
        "output_tokens": response.usage.output_tokens if response.usage else None,
        "estimated_cost_usd": estimate_cost_usd(response.model or "", response.usage),
        "tool_arguments": [{"tool": c.name, "arguments": c.arguments, "ok": c.ok, "error_type": c.error_type}
                           for c in calls],
        "error": response.error.type if response.error else None,
        "answer_preview": answer[:240],
        # Full record for manual review (the answer is already bounded by the service).
        "answer": answer,
        "citation_details": [{"evidence_id": c.evidence_id, "tool": c.tool, "kind": c.kind, "title": c.title,
                              "citation_status": c.citation_status,
                              "source_url": c.source.url if c.source else None} for c in response.citations],
        "evidence_limitations": list(response.evidence_limitations),
        "tool_call_count": len(calls),
        "tool_latency_ms": [{"tool": c.name, "latency_ms": c.latency_ms} for c in calls],
        **record,
    }


async def _run_case(case, config, mode: str, policy=None):
    from backend.ai.agent.service import run_agent
    from backend.ai.agent.testing import ScriptedChatModel, planned_policy

    capture: dict[str, Any] = {}
    model = None
    if mode == "fake":
        model = ScriptedChatModel(policy=policy or planned_policy(case["fake_plan"]))
    response = await run_agent(case["question"], config=config, chat_model=model, capture=capture)
    return score_case(case, response, capture)


def _dict_rate(rows, key, field):
    values = [r[key][field] for r in rows if r.get(key)]
    return {"passed": sum(values), "applicable": len(values), "rate": round(sum(values) / len(values), 4) if values else None}


def _rate(rows, key):
    values = [r[key] for r in rows if r[key] is not None]
    return {"passed": sum(values), "applicable": len(values), "rate": round(sum(values) / len(values), 4) if values else None}


def summarise(rows: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    latencies = [r["latency_ms"] for r in rows]
    tokens = [r["total_tokens"] for r in rows if r["total_tokens"]]
    return {
        "mode": mode,
        "interpretation": ("deterministic fake model following scripted plans: measures orchestration, evidence "
                           "handling and the evaluator - NOT real LLM accuracy") if mode == "fake"
                          else "real LLM run",
        "cases": len(rows),
        "tool_selection": _rate(rows, "tool_selection"),
        "argument_correctness": _rate(rows, "argument_correctness"),
        "citation_validity": _rate(rows, "citation_validity"),
        "fact_presence": _rate(rows, "fact_presence"),
        "concept_coverage": _dict_rate(rows, "concept_coverage", "covered"),
        "abstention": _dict_rate(rows, "abstention", "valid"),
        "support_review_flagged_sentences": sum(r.get("support_review_flagged") or 0 for r in rows),
        "groundedness": "manual evidence review required (not automated)",
        "evaluator_version": EVALUATOR_VERSION,
        "task_success": _rate(rows, "task_success"),
        "latency_ms": {"mean": round(statistics.mean(latencies), 1), "max": round(max(latencies), 1)},
        "model_calls_total": sum(r["model_calls"] for r in rows),
        "tokens_total": sum(tokens) if tokens else None,
        "estimated_cost_usd_total": round(sum(r["estimated_cost_usd"] or 0 for r in rows), 6),
    }


async def negative_controls(cases_by_id, config) -> list[dict[str, Any]]:
    """Deliberately wrong agents; each listed metric MUST come out False."""
    from backend.ai.agent.testing import ai_text, planned_policy, script

    r01 = cases_by_id["R01"]
    controls = [
        ("fabricated citation and URL", planned_policy(r01["fake_plan"], after_answer=" See [E99] https://made-up.example/x"),
         ["citation_validity"]),
        ("wrong tool for an exact question",
         planned_policy([[{"tool": "search_nobel_knowledge", "args": {"query": "2022 chemistry prize"}}]]),
         ["tool_selection", "argument_correctness"]),
        ("answer without any tool (hallucination)",
         script(ai_text("Marie Curie won the 2022 Chemistry prize [E1].")),
         ["tool_selection", "task_success", "fact_presence", "citation_validity"]),
    ]
    results = []
    for name, policy, must_fail in controls:
        row = await _run_case(r01, config, "fake", policy)
        detected = all(row[m] is False for m in must_fail)
        results.append({"control": name, "must_fail": must_fail, "detected": detected,
                        **{m: row[m] for m in must_fail}})
    return results


async def evaluate(mode: str = "fake", ids: list[str] | None = None, dataset_path: Path = DATASET,
                   max_cost_usd: float | None = None) -> dict[str, Any]:
    from backend.ai.agent.config import AgentConfig, load_agent_config

    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    known = {c["id"] for c in dataset["cases"]}
    unknown = sorted(set(ids or []) - known)
    if unknown:
        raise SystemExit(f"Unknown case id(s): {', '.join(unknown)}")
    order = {cid: i for i, cid in enumerate(ids or [])}
    cases = sorted((c for c in dataset["cases"] if not ids or c["id"] in ids),
                   key=lambda c: order.get(c["id"], 0))  # run in the order given
    if mode == "openai":
        # Load the git-ignored .env WITHOUT overriding variables already set in the
        # shell, so command-line AI_AGENT_ENABLED / AI_ALLOW_PAID_EVAL and the
        # exported DB_* settings win over the .env defaults. Values are never printed.
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)
        if os.getenv("AI_ALLOW_PAID_EVAL") != "1":
            raise SystemExit("Refusing to call a paid model: set AI_ALLOW_PAID_EVAL=1 after explicit approval.")
        config = load_agent_config()
        available, reason = config.availability()
        if not available:
            raise SystemExit(reason)
    else:
        config = AgentConfig()
    rows = []
    stopped = None
    for case in cases:
        spent = sum(r["estimated_cost_usd"] or 0 for r in rows)
        if max_cost_usd is not None and spent >= max_cost_usd:
            stopped = f"cost cap ${max_cost_usd} reached after {len(rows)} case(s) (estimated ${spent:.4f})"
            break
        rows.append(await _run_case(case, config, mode))
        if mode == "openai" and (rows[-1]["error"] or "").startswith("provider_"):
            # Authentication, model availability or request-compatibility problems
            # would repeat on every question: stop instead of spending more.
            stopped = f"stopped after {rows[-1]['id']}: {rows[-1]['error']}"
            break
    report = {"summary": summarise(rows, mode) if rows else {"mode": mode, "cases": 0}, "cases": rows}
    from backend.ai.agent.prompts import PROMPT_VERSION

    report["summary"]["prompt_version"] = PROMPT_VERSION
    report["summary"]["case_ids"] = [c["id"] for c in cases]
    if mode == "openai":
        report["summary"]["model"] = config.model
        report["summary"]["reasoning_effort"] = config.reasoning_effort
        report["summary"]["max_cost_usd"] = max_cost_usd
        report["summary"]["pricing_usd_per_1m"] = PRICING.get(config.model)
        report["summary"]["stopped_early"] = stopped
    if mode == "fake":
        report["negative_controls"] = await negative_controls({c["id"]: c for c in dataset["cases"]}, config)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the agent evaluation")
    parser.add_argument("--mode", choices=["fake", "openai"], default="fake")
    parser.add_argument("--ids", default=None, help="comma-separated case ids")
    parser.add_argument("--stage", type=int, choices=[1, 2], default=None, help="paid evaluation stage")
    parser.add_argument("--stage1-reviewed", action="store_true", help="required for stage 2")
    parser.add_argument("--max-cost-usd", type=float, default=0.50, help="stop once estimated spend reaches this")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    ids = args.ids.split(",") if args.ids else None
    if args.stage is not None:
        if args.stage == 2 and not args.stage1_reviewed:
            raise SystemExit("Stage 2 requires --stage1-reviewed after the stage 1 results have been reviewed.")
        ids = STAGES[args.stage]
    report = asyncio.run(evaluate(args.mode, ids, max_cost_usd=args.max_cost_usd if args.mode == "openai" else None))
    if args.output:
        text = json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n"
        secret = os.environ.get("OPENAI_API_KEY", "")
        if secret and secret in text:  # never write credentials to disk
            raise SystemExit("Refusing to write output: it would contain the API key.")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    for row in report["cases"]:
        failed = [k for k in ("tool_selection", "argument_correctness", "citation_validity", "fact_presence",
                              "task_success") if row[k] is False]
        if failed:
            print(f"FAIL {row['id']}: {', '.join(failed)} | {row['answer_preview'][:120]!r}")
    for control in report.get("negative_controls", []):
        print(f"NEGATIVE CONTROL {'detected' if control['detected'] else 'MISSED'}: {control['control']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
