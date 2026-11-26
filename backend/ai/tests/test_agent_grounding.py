"""Regression cases for the revised deterministic answer checks (no LLM, no DB)."""

from backend.ai.evaluation.grounding import (
    abstention_check,
    citation_support_review,
    concept_coverage,
    evidence_texts,
)

DOE_TEXT = ("Photoelectric Effect - Application: Solar Panels / Photovoltaic Technology. Modern photovoltaic cells "
            "absorb photons in semiconductors to generate electron-hole charge carriers, then separate and collect "
            "those carriers as electrical current.")
EINSTEIN_TEXT = ("Albert Einstein 1921 Physics for his services to Theoretical Physics, and especially for his "
                 "discovery of the law of the photoelectric effect")
BERTOZZI_TEXT = "Carolyn R. Bertozzi 2022 Chemistry for the development of click chemistry and bioorthogonal chemistry"


# ---------------------------------------------------------------- abstention (R09)

def test_real_r09_answer_is_a_valid_abstention():
    answer = "Nobel Explorer has no reliable evidence about sourdough fermentation; its search returned only weakly related material."
    result = abstention_check(answer, citation_count=0)
    assert result["valid"] and result["phrase"] == "no reliable evidence"


def test_other_abstention_phrasings_are_accepted():
    for answer in ("There is insufficient evidence in Nobel Explorer to answer this.",
                   "I found no relevant information about that. Would you like to ask about a Nobel laureate instead?"):
        assert abstention_check(answer, citation_count=0)["valid"], answer


def test_abstention_followed_by_unsupported_claims_is_rejected():
    answer = ("Nobel Explorer has no reliable evidence about sourdough. However, sourdough is fermented by wild "
              "yeast and lactic acid bacteria over 12 hours.")
    result = abstention_check(answer, citation_count=0)
    assert not result["valid"] and result["reason"] == "abstention followed by claims"
    assert "wild yeast" in result["unsupported_sentences"][0]


def test_abstention_with_citations_is_rejected():
    assert not abstention_check("Insufficient evidence, but Buchner studied fermentation [E2].", 1)["valid"]


def test_answer_without_abstention_phrase_is_rejected():
    assert abstention_check("Sourdough uses a starter culture.", 0)["reason"] == "no abstention phrase"


# ---------------------------------------------------------------- concept coverage (R07)

R07_CONCEPTS = [["photovoltaic", "solar cell", "semiconductor"], ["photon", "light"],
                ["charge carrier", "electron", "hole", "current"]]


def test_correct_paraphrase_without_expected_keyword_is_covered():
    answer = ("Solar cells use semiconductor materials to turn light into electrical current. Photons absorbed by "
              "the semiconductor generate mobile charge carriers [E1].")
    assert "photovoltaic" not in answer.lower()
    assert concept_coverage(answer, R07_CONCEPTS)["covered"]


def test_missing_concept_is_reported():
    result = concept_coverage("Solar cells make electricity.", R07_CONCEPTS)
    assert not result["covered"] and ["photon", "light"] in result["missing_concepts"]


# ---------------------------------------------------------------- citation support review

def test_supported_sentence_is_lexically_supported():
    review = citation_support_review("Photons absorbed in semiconductors generate charge carriers collected as current [E1].",
                                     {"E1": DOE_TEXT})
    assert review["flagged"] == 0


def test_valid_citation_attached_to_unsupported_claim_is_flagged():
    # E1 exists (citation validity passes) but says 2022 Chemistry, not 1990 Physics.
    review = citation_support_review("Carolyn Bertozzi won the 1990 Nobel Prize in Physics [E1].", {"E1": BERTOZZI_TEXT})
    row = review["sentences"][0]
    assert row["status"] == "review" and row["missing_numbers"] == ["1990"]


def test_correct_statement_not_supported_by_retrieved_evidence_is_flagged():
    # True, but the retrieved motivation never mentions relativity (R02/R10 pattern).
    review = citation_support_review(
        "Einstein was not awarded the prize for general relativity [E1].", {"E1": EINSTEIN_TEXT})
    row = review["sentences"][0]
    assert row["status"] == "review" and {"general", "relativity"} <= set(row["terms_not_in_cited_evidence"])


def test_lexical_review_cannot_detect_negation():
    # Documented limitation: same words, opposite meaning -> not flagged.
    review = citation_support_review(
        "Einstein did not discover the law of the photoelectric effect [E1].", {"E1": EINSTEIN_TEXT})
    assert review["flagged"] == 0 and "cannot establish factual entailment" in review["note"]


def test_uncited_sentences_are_reported():
    review = citation_support_review("Bertozzi won [E1]. She also likes hiking.", {"E1": BERTOZZI_TEXT})
    assert [r["status"] for r in review["sentences"]][1] == "uncited"


def test_evidence_texts_from_captured_tool_results():
    results = [{"name": "search_laureates", "result": {"ok": True, "data": {"laureates": [
        {"evidence_id": "E1", "full_name": "Carolyn R. Bertozzi",
         "matched_awards": [{"year": 2022, "category": "Chemistry", "motivation": "for click chemistry"}],
         "other_awards": []}]}}},
        {"name": "search_nobel_knowledge", "result": {"ok": True, "data": {"results": [
            {"evidence_id": "E2", "title": "Solar", "text": "photovoltaic cells"}]}}}]
    texts = evidence_texts(results)
    assert "2022 Chemistry for click chemistry" in texts["E1"] and "photovoltaic" in texts["E2"]


def test_small_unsupported_addition_inside_supported_sentence_is_flagged():
    # Regression: an overlap threshold hid this (7 of 9 terms supported).
    review = citation_support_review(
        "Einstein received the 1921 Nobel Prize in Physics for theoretical physics and the photoelectric effect, "
        "not for general relativity [E1].", {"E1": EINSTEIN_TEXT})
    row = review["sentences"][0]
    assert row["status"] == "review" and "relativity" in row["terms_not_in_cited_evidence"]
    assert row["term_overlap"] > 0.6  # high overlap, still flagged


def test_inflected_paraphrase_is_not_flagged():
    review = citation_support_review("Photons absorbed in semiconductors generate carriers [E1].", {"E1": DOE_TEXT})
    assert review["flagged"] == 0


def test_citation_after_full_stop_belongs_to_previous_sentence():
    # Regression: "[E1]" after the period was treated as its own sentence.
    review = citation_support_review("Einstein won for the photoelectric effect, not for relativity. [E1]",
                                     {"E1": EINSTEIN_TEXT})
    assert len(review["sentences"]) == 1 and review["sentences"][0]["cited"] == ["E1"]
    assert "relativity" in review["sentences"][0]["terms_not_in_cited_evidence"]


def test_paragraph_final_citation_covers_its_sentences():
    answer = "Solar cells absorb photons in semiconductors. Charges flow through an external circuit. [E1]"
    rows = citation_support_review(answer, {"E1": DOE_TEXT})["sentences"]
    assert [r["cited"] for r in rows] == [["E1"], ["E1"]]
    assert rows[0]["citation_inherited_from_paragraph"] and rows[0]["status"] == "lexically_supported"
    assert rows[1]["status"] == "review" and {"external", "circuit"} <= set(rows[1]["terms_not_in_cited_evidence"])
