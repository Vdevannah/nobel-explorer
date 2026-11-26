"""Scripted tool evaluation (Phase 2).

    python -m backend.ai.evaluation.run_tool_eval [--output PATH]

For every case the EXPECTED tools are invoked directly through their
LangChain interface with the recorded arguments, and the results are checked.
This measures whether the tools return correct, well-formed answers when
called correctly. It is NOT a measure of an LLM's ability to choose tools or
arguments; that is evaluated in Phase 3.

Path mini-language for checks and argument references:
  a.b.0.c         keys and list indexes
  a.*.b           map over a list
  a.[k=v].b       first list element whose field k equals v (string compare)
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

DATASET = Path(__file__).with_name("tool_eval_set.json")
_MISSING = object()
_SEGMENT = re.compile(r"\[[^\]]*\]|[^.]+")


def resolve(data: Any, path: str) -> Any:
    current = data
    segments = _SEGMENT.findall(path)  # bracket-aware: "[full_name=Carolyn R. Bertozzi]" stays whole
    for i, segment in enumerate(segments):
        if current is _MISSING:
            return _MISSING
        if segment == "*":
            rest = ".".join(segments[i + 1:])  # rejoin; re-tokenised by the recursive call
            return [resolve(item, rest) if rest else item for item in current]
        if segment.startswith("[") and segment.endswith("]"):
            key, _, value = segment[1:-1].partition("=")
            current = next((item for item in current if str(item.get(key)) == value), _MISSING)
        elif isinstance(current, list):
            index = int(segment)
            current = current[index] if -len(current) <= index < len(current) else _MISSING
        elif isinstance(current, dict):
            current = current.get(segment, _MISSING)
        else:
            return _MISSING
    return current


def _check(result: dict[str, Any], expectation: dict[str, Any]) -> tuple[bool, str]:
    actual = resolve(result, expectation["path"])
    if actual is _MISSING:
        return False, f"{expectation['path']} is missing"
    if "equals" in expectation:
        ok = actual == expectation["equals"]
        return ok, f"{expectation['path']} == {expectation['equals']!r} (actual {actual!r})"
    if "contains" in expectation:
        ok = isinstance(actual, str) and expectation["contains"] in actual
        return ok, f"{expectation['path']} contains {expectation['contains']!r}"
    if "any_in_first" in expectation:
        spec = expectation["any_in_first"]
        ok = any(v in spec["values"] for v in actual[: spec["k"]])
        return ok, f"any of {spec['values']} in first {spec['k']} of {actual[: spec['k']]}"
    return False, f"unknown expectation {expectation}"


def _resolve_args(args: dict[str, Any], previous: list[dict[str, Any]]) -> dict[str, Any]:
    resolved = {}
    for key, value in args.items():
        if isinstance(value, dict) and "$ref" in value:
            value = resolve(previous[value["$ref"]], value["path"])
            if value is _MISSING:
                raise ValueError(f"argument {key}: reference could not be resolved")
        resolved[key] = value
    return resolved


def evaluate(registry=None, dataset_path: Path = DATASET) -> dict[str, Any]:
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if registry is None:
        from backend.ai.tools import get_tool_registry
        registry = get_tool_registry()

    cases = []
    tool_calls = Counter()
    for case in dataset["cases"]:
        outputs: list[dict[str, Any]] = []
        step_reports = []
        case_ok = True
        for step in case["steps"]:
            try:
                args = _resolve_args(step["args"], outputs)
            except (ValueError, IndexError, TypeError) as exc:
                step_reports.append({"tool": step["tool"], "args": step["args"], "ok": False, "passed": False,
                                     "checks": [{"passed": False, "detail": f"argument resolution failed: {exc}"}],
                                     "latency_ms": None, "note": step.get("note")})
                case_ok = False
                break
            started = time.perf_counter()
            output = registry[step["tool"]].invoke(args)
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            outputs.append(output)
            tool_calls[step["tool"]] += 1
            checks = [dict(zip(("passed", "detail"), _check(output, e))) for e in step["expect"]]
            json.dumps(output, allow_nan=False)  # must be serialisable
            step_ok = all(c["passed"] for c in checks)
            case_ok &= step_ok
            step_reports.append({"tool": step["tool"], "args": args, "ok": output["ok"], "passed": step_ok,
                                 "checks": checks, "latency_ms": latency_ms, "note": step.get("note")})
        cases.append({"id": case["id"], "group": case["group"], "question": case["question"],
                      "passed": case_ok, "steps": step_reports})

    by_group: dict[str, list[bool]] = {}
    for c in cases:
        by_group.setdefault(c["group"], []).append(c["passed"])
    latencies = sorted(s["latency_ms"] for c in cases for s in c["steps"] if s["latency_ms"] is not None)
    return {
        "mode": "scripted: expected tools invoked directly; not LLM tool-selection accuracy",
        "cases": len(cases),
        "passed": sum(c["passed"] for c in cases),
        "tool_calls": dict(tool_calls),
        "by_group": {g: f"{sum(v)}/{len(v)}" for g, v in sorted(by_group.items())},
        "latency_ms": {"median": latencies[len(latencies) // 2], "max": latencies[-1]},
        "failures": [c for c in cases if not c["passed"]],
        "results": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the scripted tool evaluation")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    report = evaluate()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("mode", "cases", "passed", "tool_calls", "by_group", "latency_ms")},
                     indent=2))
    for failure in report["failures"]:
        for step in failure["steps"]:
            for check in step["checks"]:
                if not check["passed"]:
                    print(f"FAIL {failure['id']} {step['tool']}: {check['detail']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
