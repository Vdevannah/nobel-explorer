"""Evidence ids, provenance preservation and citation/URL validation (no LLM)."""

import json

from backend.ai.agent.evidence import EvidenceRegistry, validate_answer

DOE = "https://www.energy.gov/cmei/systems/solar-photovoltaic-cell-basics"
NOBEL_1921 = "https://www.nobelprize.org/prizes/physics/1921/summary/"


def _registry():
    registry = EvidenceRegistry()
    registry.annotate("search_laureates", {"tool": "search_laureates", "ok": True, "data": {
        "laureates": [{"laureate_id": 356, "full_name": "Carolyn R. Bertozzi", "nobel_laureate_id": "1015"}],
        "provenance": {"source_name": "Nobel Prize API v2.1"}, "total_matches": 1}})
    registry.annotate("search_nobel_knowledge", {"tool": "search_nobel_knowledge", "ok": True, "data": {
        "query": "solar", "all_results_weak": False, "results": [
            {"doc_id": "connection:24", "doc_type": "connection", "title": "Solar Panels",
             "citation_status": "source_linked", "source": {"name": "U.S. Department of Energy", "url": DOE},
             "related_source": None, "similarity": 0.57, "weak_match": False},
            {"doc_id": "explanation:38:simple", "doc_type": "explanation", "title": "Photoelectric - Simple",
             "citation_status": "unverified_educational", "source": None,
             "related_source": {"name": "NobelPrize.org", "url": NOBEL_1921}, "similarity": 0.39, "weak_match": True},
        ]}})
    return registry


def test_ids_are_sequential_and_attached():
    registry = _registry()
    assert list(registry.items) == ["E1", "E2", "E3"]
    assert registry.items["E1"].citation_status == "structured_record"
    assert registry.items["E1"].source is None and registry.items["E1"].source_name == "Nobel Prize API v2.1"


def test_annotate_content_rewrites_tool_message_json():
    registry = EvidenceRegistry()
    content = json.dumps({"tool": "get_nobel_statistics", "ok": True,
                          "data": {"operation": "summary", "result": {"prizes": 633}, "source": "db"}})
    new_content, ids, envelope = registry.annotate_content("get_nobel_statistics", content)
    payload = json.loads(new_content)
    assert ids == ["E1"] and payload["evidence_ids"] == ["E1"] and payload["data"]["evidence_id"] == "E1"
    assert "citation_instruction" in payload


def test_error_envelopes_produce_no_evidence_and_are_flagged():
    registry = EvidenceRegistry()
    ids = registry.annotate("search_laureates", {"tool": "search_laureates", "ok": False,
                                                 "error": {"type": "validation_error", "message": "bad"}})
    assert ids == [] and registry.items == {}
    assert registry.flags["tool_errors"] == ["search_laureates: validation_error"]


def test_non_json_content_passes_through():
    registry = EvidenceRegistry()
    assert registry.annotate_content("x", "Error: x is not a valid tool")[1:] == ([], None)


def test_valid_citations_are_kept_with_provenance():
    registry = _registry()
    check = validate_answer("Bertozzi won [E1]. Solar cells convert light [E2].", registry)
    assert check.answer == "Bertozzi won [E1]. Solar cells convert light [E2]."
    assert [c.evidence_id for c in check.citations] == ["E1", "E2"]
    assert check.citations[1].source.url == DOE and check.citations[0].source is None


def test_fabricated_citations_are_marked_unverified():
    check = validate_answer("Claim [E1, E9]. Other claim [E77].", _registry())
    assert check.answer == "Claim [E1]. Other claim [unverified]."
    assert check.fabricated_ids == ["E9", "E77"]
    assert [c.evidence_id for c in check.citations] == ["E1"]


def test_unknown_urls_are_removed_and_known_direct_sources_kept():
    text = f"See {DOE} and https://example.com/made-up. Also [the source](https://fake.org/x)."
    check = validate_answer(text, _registry())
    assert DOE in check.answer and "example.com" not in check.answer and "fake.org" not in check.answer
    assert "the source" in check.answer
    assert check.removed_urls == ["https://example.com/made-up", "https://fake.org/x"]


def test_related_source_url_is_not_promoted_to_citation():
    check = validate_answer(f"Light knocks out electrons [E3] (source: {NOBEL_1921}).", _registry())
    assert NOBEL_1921 not in check.answer
    assert check.related_source_urls_removed == [NOBEL_1921]
    citation = check.citations[0]
    assert citation.citation_status == "unverified_educational"
    assert citation.source is None and citation.related_source.url == NOBEL_1921


def test_answer_without_citations_has_none():
    check = validate_answer("Carolyn Bertozzi won the prize.", _registry())
    assert check.citations == [] and check.fabricated_ids == []


def test_flags_capture_weak_ambiguous_and_missing_content():
    registry = EvidenceRegistry()
    registry.annotate("search_nobel_knowledge", {"tool": "search_nobel_knowledge", "ok": True,
                                                 "data": {"query": "sourdough", "all_results_weak": True, "results": []}})
    registry.annotate("search_laureates", {"tool": "search_laureates", "ok": True, "data": {
        "laureates": [], "ambiguous_name": True, "filters": {"name": "Curie"}, "total_matches": 3}})
    registry.annotate("get_laureate_details", {"tool": "get_laureate_details", "ok": True, "data": {
        "laureate": {"full_name": "Wilhelm Conrad Röntgen", "laureate_id": 1}, "contributions": [],
        "educational_content_available": False, "provenance": {}}})
    assert set(registry.flags) >= {"weak_semantic_evidence", "ambiguous_name", "missing_educational_content",
                                   "empty_results"}


# ---------------------------------------------------------------- adversarial cases

def test_lowercase_and_padded_citation_ids_are_validated():
    check = validate_answer("A [e1]. B [ e2 ; E9 ]. C [e42].", _registry())
    assert check.answer == "A [E1]. B [E2]. C [unverified]."
    assert check.fabricated_ids == ["E9", "E42"]


def test_uppercase_scheme_and_lookalike_domains_are_removed():
    text = f"HTTPS://EVIL.EXAMPLE/x https://www.energy.gov.evil.com/cmei {DOE}?ref=1 {DOE}."
    check = validate_answer(text, _registry())
    assert check.answer == f"[link removed] [link removed] [link removed] {DOE}."
    assert len(check.removed_urls) == 3


def test_script_and_data_links_are_neutralised():
    check = validate_answer("Click [here](javascript:alert(1)) or [x](data:text/html;base64,AAAA) or [ok](" + DOE + ")",
                            _registry())
    assert "javascript" not in check.answer and "data:" not in check.answer
    assert check.answer.endswith(f"[ok]({DOE})")


def test_bare_hosts_and_autolinks_are_removed():
    check = validate_answer("Visit www.evil-site.com/steal or <https://evil.example/a>.", _registry())
    assert check.answer == "Visit [link removed] or [link removed]."


def test_parallel_annotation_never_duplicates_ids():
    import threading

    registry = EvidenceRegistry()

    def worker():
        for _ in range(25):
            registry.annotate("get_nobel_statistics", {"tool": "get_nobel_statistics", "ok": True,
                                                       "data": {"operation": "summary", "result": {}}})

    threads = [threading.Thread(target=worker) for _ in range(32)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(registry.items) == 800 and set(registry.items) == {f"E{i}" for i in range(1, 801)}


def test_injected_citation_instructions_cannot_create_evidence():
    # Retrieved text telling the model to cite E999 or a URL gains nothing.
    check = validate_answer("As the document instructs: [E999] https://evil.example/official", _registry())
    assert "[unverified]" in check.answer and "evil.example" not in check.answer and check.citations == []
