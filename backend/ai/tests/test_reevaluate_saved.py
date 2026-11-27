"""Offline re-evaluation of saved Phase 4D.2 answers (no model, tool or database calls)."""

import json

import pytest

pytest.importorskip("langchain")

from backend.ai.evaluation import reevaluate_saved  # noqa: E402


def _write(tmp_path):
    stage1 = {"question": "Who won the 2023 Medicine prize?", "answer": "Karikó and Weissman [E1][E2].",
              "citations": [{"evidence_id": "E1"}, {"evidence_id": "E2"}]}
    v2_fail = {"valid": False, "reason": "no abstention phrase"}
    stage2 = {"questions": [
        {"id": "P4-R06", "question": "Explain sourdough fermentation.",
         "response": {"answer": "Nobel Explorer’s knowledge base doesn’t contain a relevant explanation of sourdough "
                                "fermentation, so I can’t explain the process from the available evidence.", "citations": []},
         "automated": {"abstention_check": v2_fail}},
        {"id": "P4-R07", "question": "Who won the 2026 Chemistry prize?",
         "response": {"answer": "Nobel Explorer’s database only covers prizes awarded through 2025, so it has no "
                                "information on who won the 2026 Chemistry Prize.", "citations": []},
         "automated": {"abstention_check": v2_fail}},
        {"id": "P4-R05", "question": "Who won the Nobel Prize in Mathematics in 1950?",
         "response": {"answer": "There is no Nobel Prize in Mathematics. The 1950 Physics prize went to Powell [E1].",
                      "citations": [{"evidence_id": "E1"}]},
         "automated": {"abstention_check": v2_fail}},
    ]}
    p1, p2 = tmp_path / "s1.json", tmp_path / "s2.json"
    p1.write_text(json.dumps(stage1), encoding="utf-8")
    p2.write_text(json.dumps(stage2), encoding="utf-8")
    return p1, p2


def test_phase4d2_reevaluation_reports_original_and_revised_separately(tmp_path):
    p1, p2 = _write(tmp_path)
    before = (p1.read_bytes(), p2.read_bytes())
    report = reevaluate_saved.reevaluate_phase4d2(p1, p2)
    assert report["evaluator_version"] == 3
    assert report["summary"]["expected_abstentions_recognised"] == {"original_v2": "0/2", "revised_v3": "2/2"}
    assert report["summary"]["abstention_kind_correct_v3"] == "2/2"
    assert report["summary"]["false_abstentions_on_answers"]["revised_v3"] == "0/2"
    rows = {r["id"]: r for r in report["cases"]}
    assert rows["P4-R07"]["revised_v3"]["kind"] == "coverage"
    assert rows["P4-R03"]["original_v2"] is None
    assert (p1.read_bytes(), p2.read_bytes()) == before  # inputs are read only


def test_cli_refuses_to_overwrite_an_input(tmp_path):
    p1, p2 = _write(tmp_path)
    with pytest.raises(SystemExit, match="Refusing to overwrite"):
        reevaluate_saved.main(["--phase4d2-stage1", str(p1), "--phase4d2-stage2", str(p2), "--output", str(p2)])


def test_cli_rejects_mixed_modes(tmp_path):
    p1, p2 = _write(tmp_path)
    with pytest.raises(SystemExit, match="together"):
        reevaluate_saved.main(["--phase4d2-stage1", str(p1), "--stage1", str(p1), "--output", str(tmp_path / "o.json")])


def test_revised_block_is_named_after_the_evaluator_version():
    assert reevaluate_saved.REVISED_KEY == f"revised_v{reevaluate_saved.EVALUATOR_VERSION}" == "revised_v3"
