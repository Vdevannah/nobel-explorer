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
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.ai.evaluation.run_agent_eval import DATASET, EVALUATOR_VERSION, score_core

ORIGINAL_KEYS = ("tool_selection", "argument_correctness", "citation_validity", "groundedness", "task_success")


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
        "revised_v2": revised,
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
            "revised_v2": {k: count("revised_v2", k) for k in
                           ("tool_selection", "argument_correctness", "citation_validity", "fact_presence", "task_success")}
            | {"groundedness": "manual evidence review required",
               "support_review_flagged_sentences": sum(r["revised_v2"].get("support_review_flagged") or 0 for r in rows)},
        },
        "cases": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stage1", type=Path, required=True)
    parser.add_argument("--stage2", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.resolve() in {args.stage1.resolve(), args.stage2.resolve()}:
        raise SystemExit("Refusing to overwrite an original evaluation file.")
    report = reevaluate(args.stage1, args.stage2)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
