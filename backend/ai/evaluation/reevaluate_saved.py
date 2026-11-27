"""Offline re-evaluation of SAVED real-model responses (no model or tool calls).

    python -m backend.ai.evaluation.reevaluate_saved \
        --stage1 ai_index/agent_eval_openai_stage1.json \
        --stage2 ai_index/agent_eval_openai_stage2_full.json \
        --output ai_index/agent_eval_openai_offline_reeval_v2.json

Applies evaluator v2 and dataset v2 to the answers, tool calls, citations and
tool results recorded during the original paid runs. The original files and
scores are read only and reported side by side; nothing is overwritten.
Stage 1 records (R01) lack tool results and citation details, so only the
answer-text checks can be re-run for them; other values are carried over and
labelled "original".

Phase 4D.2 saved browser results (evaluator v3 abstention re-check):

    python -m backend.ai.evaluation.reevaluate_saved \
        --phase4d2-stage1 docs/teaching/phase4_real_model_screenshots/phase4d2_stage1_result.json \
        --phase4d2-stage2 docs/teaching/phase4_real_model_screenshots/stage2/phase4d2_stage2_results.json \
        --output ai_index/agent_eval_openai_phase4d2_offline_reeval_v3.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.ai.evaluation.grounding import abstention_check
from backend.ai.evaluation.run_agent_eval import DATASET, EVALUATOR_VERSION, score_core

ORIGINAL_KEYS = ("tool_selection", "argument_correctness", "citation_validity", "groundedness", "task_success")
# The revised block is named after the evaluator that produced it (Phase 4E.2 fix: it was
# hard-coded as "revised_v2" even when EVALUATOR_VERSION was 3). Scoring logic is unchanged.
REVISED_KEY = f"revised_v{EVALUATOR_VERSION}"


def reevaluate_row(case: dict[str, Any], row: dict[str, Any], source: str) -> dict[str, Any]:
    full_record = "answer" in row and "tool_results" in row
    answer = row.get("answer") if "answer" in row else row.get("answer_preview", "")
    calls = [(c["tool"], c["arguments"]) for c in row.get("tool_arguments", [])]
    if full_record:
        statuses = [c["citation_status"] for c in row.get("citation_details", [])]
        tampered = row.get("grounding") == "partially_cited" or any(
            "Removed" in note for note in row.get("evidence_limitations", []))
        revised = score_core(case, answer=answer, status=row["status"], calls=calls, citation_statuses=statuses,
                             citations_tampered=tampered, tool_results=row.get("tool_results"))
    else:
        # Answer-text checks only; citation validity cannot be recomputed from this record.
        revised = score_core(case, answer=answer, status=row["status"], calls=calls,
                             citation_statuses=["unknown"] * row.get("citations", 0),
                             citations_tampered=None, tool_results=None)
        revised["citation_validity"] = {"value": row["citation_validity"], "source": "original (not re-evaluable)"}
    return {
        "id": row["id"], "question": row["question"], "source_file": source,
        "record": "full" if full_record else "stage1 summary (answer preview <= 240 chars, no tool results)",
        "answer_complete": full_record or len(answer) < 240,
        "original_v1": {k: row.get(k) for k in ORIGINAL_KEYS},
        REVISED_KEY: revised,
    }


def reevaluate(stage1: Path, stage2: Path) -> dict[str, Any]:
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    cases = {c["id"]: c for c in dataset["cases"]}
    s1 = json.loads(stage1.read_text(encoding="utf-8"))
    s2 = json.loads(stage2.read_text(encoding="utf-8"))
    rows = [reevaluate_row(cases["R01"], next(r for r in s1["cases"] if r["id"] == "R01"), stage1.name)]
    rows += [reevaluate_row(cases[r["id"]], r, stage2.name) for r in s2["cases"]]
    order = [f"R{i:02d}" for i in range(1, 11)]
    rows.sort(key=lambda r: order.index(r["id"]))

    def count(version: str, key: str) -> str:
        values = []
        for r in rows:
            value = r[version][key]
            if isinstance(value, dict):
                value = value.get("value")
            if value is not None:
                values.append(bool(value))
        return f"{sum(values)}/{len(values)}"

    return {
        "label": ("OFFLINE RE-EVALUATION of saved real-model responses (gpt-6-luna). No model or tool calls were made. "
                  "Original real-model scores are unchanged and shown as original_v1."),
        "evaluator_version": EVALUATOR_VERSION,
        "dataset_version": dataset["version"],
        "prompt_versions_of_saved_runs": {"R01": s1["summary"].get("prompt_version", "2026-11-26.1"),
                                          "R02-R10": s2["summary"].get("prompt_version")},
        "summary": {
            "original_v1": {k: count("original_v1", k) for k in ORIGINAL_KEYS},
            REVISED_KEY: {k: count(REVISED_KEY, k) for k in
                           ("tool_selection", "argument_correctness", "citation_validity", "fact_presence", "task_success")}
            | {"groundedness": "manual evidence review required",
               "support_review_flagged_sentences": sum(r[REVISED_KEY].get("support_review_flagged") or 0 for r in rows)},
        },
        "cases": rows,
    }


# Phase 4D.2 questions whose correct behaviour is an abstention (manual review), and its kind.
PHASE4D2_EXPECTED_ABSTENTION = {"P4-R06": "insufficient_evidence", "P4-R07": "coverage"}


def reevaluate_phase4d2(stage1: Path, stage2: Path) -> dict[str, Any]:
    """Re-run the answer-level abstention check (evaluator v3) on the saved Phase 4D.2 answers.

    The saved real-model answers, citations and original (v2) automated results are read only.
    Only the abstention check changes in v3; citation validation and the lexical support review
    are carried over unchanged from the original artifacts.
    """
    s1 = json.loads(stage1.read_text(encoding="utf-8"))
    s2 = json.loads(stage2.read_text(encoding="utf-8"))
    records = [{"id": "P4-R03", "question": s1["question"], "answer": s1["answer"], "citations": len(s1["citations"]),
                "original_abstention_v2": None}]
    records += [{"id": q["id"], "question": q["question"], "answer": q["response"]["answer"],
                 "citations": len(q["response"]["citations"]), "original_abstention_v2": q["automated"]["abstention_check"]}
                for q in s2["questions"]]
    rows = []
    for record in sorted(records, key=lambda r: r["id"]):
        revised = abstention_check(record["answer"], record["citations"])
        expected = PHASE4D2_EXPECTED_ABSTENTION.get(record["id"])
        original = record["original_abstention_v2"]
        rows.append({
            "id": record["id"], "question": record["question"], "expected_abstention": expected,
            "original_v2": None if original is None else {"valid": original["valid"], "reason": original["reason"]},
            "revised_v3": {"valid": revised["valid"], "kind": revised["kind"], "reason": revised["reason"]},
            "revised_correct": (revised["valid"] and revised["kind"] == expected) if expected else not revised["valid"],
        })
    expected_rows = [r for r in rows if r["expected_abstention"]]
    answer_rows = [r for r in rows if not r["expected_abstention"]]
    return {
        "label": ("OFFLINE RE-EVALUATION (evaluator v3) of saved Phase 4D.2 real-model answers (gpt-6-luna, prompt "
                  "2026-11-26.3). No model or tool calls. Answers are unchanged; only the deterministic abstention "
                  "check changed, so any difference reflects the evaluator, not the model."),
        "evaluator_version": EVALUATOR_VERSION,
        "source_files": [stage1.name, stage2.name],
        "summary": {
            "expected_abstentions_recognised": {
                "original_v2": f"{sum(bool(r['original_v2'] and r['original_v2']['valid']) for r in expected_rows)}/{len(expected_rows)}",
                "revised_v3": f"{sum(r['revised_v3']['valid'] for r in expected_rows)}/{len(expected_rows)}",
            },
            "abstention_kind_correct_v3": f"{sum(r['revised_correct'] for r in expected_rows)}/{len(expected_rows)}",
            "false_abstentions_on_answers": {
                "original_v2": f"{sum(bool(r['original_v2'] and r['original_v2']['valid']) for r in answer_rows)}/"
                               f"{sum(r['original_v2'] is not None for r in answer_rows)} (P4-R03 has no saved v2 result)",
                "revised_v3": f"{sum(r['revised_v3']['valid'] for r in answer_rows)}/{len(answer_rows)}",
            },
            "unchanged_from_original": "citation validation and lexical support review (not affected by v3)",
        },
        "cases": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stage1", type=Path)
    parser.add_argument("--stage2", type=Path)
    parser.add_argument("--phase4d2-stage1", type=Path)
    parser.add_argument("--phase4d2-stage2", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.phase4d2_stage1 or args.phase4d2_stage2:
        if not (args.phase4d2_stage1 and args.phase4d2_stage2) or args.stage1 or args.stage2:
            raise SystemExit("Use --phase4d2-stage1 and --phase4d2-stage2 together, without --stage1/--stage2.")
        sources = {args.phase4d2_stage1.resolve(), args.phase4d2_stage2.resolve()}
    elif args.stage1 and args.stage2:
        sources = {args.stage1.resolve(), args.stage2.resolve()}
    else:
        raise SystemExit("Provide --stage1 and --stage2, or --phase4d2-stage1 and --phase4d2-stage2.")
    if args.output.resolve() in sources:
        raise SystemExit("Refusing to overwrite an original evaluation file.")
    report = (reevaluate_phase4d2(args.phase4d2_stage1, args.phase4d2_stage2) if args.phase4d2_stage1
              else reevaluate(args.stage1, args.stage2))
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
