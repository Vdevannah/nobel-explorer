"""Deterministic answer checks used by the revised (v2) agent evaluation.

What these checks can and cannot do
-----------------------------------
* ``abstention_check``  - recognises a correct "I don't have evidence" answer,
  but rejects it if the answer goes on to make claims (cited or not).
* ``concept_coverage``  - did the answer address each expected concept? Each
  concept is a group of acceptable terms, so a correct paraphrase passes
  ("solar cell ... semiconductor" covers the photovoltaic concept).
* ``citation_support_review`` - for every sentence, lists numbers and content
  terms that do NOT occur in the text of the evidence it cites. This is a
  lexical REVIEW AID: it can flag a wrong year behind a valid citation or a
  claim that comes from somewhere other than the cited evidence, but it
  cannot prove entailment (it misses negations and paraphrased contradictions,
  and flags harmless paraphrases). Claim-level grounding therefore still
  requires MANUAL evidence review; no paid LLM judge is used.
"""

from __future__ import annotations

import json
import re
from typing import Any

ABSTENTION_PHRASES = (
    "no reliable evidence", "insufficient evidence", "not enough evidence", "no evidence",
    "no relevant information", "does not contain relevant", "doesn't contain relevant",
    "only weakly related", "weakly related material", "not covered", "outside the scope",
    "outside nobel explorer", "cannot answer", "can't answer", "unable to answer",
)
# Sentences allowed next to an abstention: offers or redirects, not claims.
_REDIRECT = re.compile(r"\?$|^(i can|i could|you can|you could|would you|if you|nobel explorer (covers|can))",
                       re.IGNORECASE)
_SENTENCES = re.compile(r"(?<=[.!?])\s+|\n+")
_CITATION = re.compile(r"\[\s*E\d+(?:\s*[,;]\s*E\d+)*\s*\]", re.IGNORECASE)
_STOP = {
    "the", "and", "for", "with", "that", "this", "these", "those", "from", "into", "their", "they", "them", "its",
    "was", "were", "are", "is", "been", "being", "have", "has", "had", "which", "who", "whom", "what", "when",
    "where", "why", "how", "also", "both", "each", "more", "most", "such", "than", "then", "there", "here",
    "about", "over", "under", "between", "through", "while", "would", "could", "should", "can", "may", "not",
    "nobel", "prize", "prizes", "laureate", "laureates", "awarded", "received", "won", "shared", "especially",
    "explorer", "simple", "explanation", "called", "like", "make", "makes", "made", "help", "helps", "helping",
    "use", "uses", "used", "using", "one", "two", "three", "first", "only", "very", "much", "many", "other",
}


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCES.split(text or "") if s.strip()]


def abstention_check(answer: str, citation_count: int) -> dict[str, Any]:
    """Valid only if an abstention phrase is present AND nothing else is asserted."""
    sentences = _sentences(answer)
    lowered = (answer or "").lower()
    phrase = next((p for p in ABSTENTION_PHRASES if p in lowered), None)
    extra = [s for s in sentences if not any(p in s.lower() for p in ABSTENTION_PHRASES) and not _REDIRECT.search(s)]
    valid = phrase is not None and citation_count == 0 and not extra
    reason = ("ok" if valid else "no abstention phrase" if phrase is None
              else "abstention followed by cited claims" if citation_count else "abstention followed by claims")
    return {"valid": valid, "phrase": phrase, "unsupported_sentences": extra, "reason": reason}


def concept_coverage(answer: str, concepts: list[list[str]]) -> dict[str, Any]:
    lowered = (answer or "").lower()
    missing = [group for group in concepts if not any(term.lower() in lowered for term in group)]
    return {"covered": not missing, "missing_concepts": missing}


def _content_terms(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-zà-ÿ]+", (text or "").lower()) if len(w) > 3 and w not in _STOP}


def _term_in(term: str, evidence: str) -> bool:
    """Prefix match (about 60% of the word, at least 5 letters): absorbed~absorb, synthesizing~synthesis."""
    return term[: max(5, int(len(term) * 0.6))] in evidence


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:[.,]\d+)?", (text or "").replace(",", "")))


def evidence_texts(tool_results: list[dict[str, Any]]) -> dict[str, str]:
    """Map each evidence id to the text the tool actually returned for it."""
    texts: dict[str, str] = {}

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            eid = node.get("evidence_id")
            if eid:
                if "matched_awards" in node or "other_awards" in node:   # laureate record
                    awards = node.get("matched_awards", []) + node.get("other_awards", [])
                    texts[eid] = node.get("full_name", "") + " " + " ".join(
                        f"{a.get('year')} {a.get('category')} {a.get('motivation') or ''} {a.get('prize_share') or ''}"
                        for a in awards)
                elif "text" in node:                                       # knowledge chunk or explanation
                    texts[eid] = f"{node.get('title', '')} {node['text']}"
                elif "result" in node:                                     # statistic
                    texts[eid] = json.dumps(node.get("result")) + " " + str(node.get("counting_unit", ""))
                else:                                                      # details, contribution, connection
                    texts[eid] = " ".join(str(node.get(k, "")) for k in
                                          ("full_name", "title", "summary", "significance", "description", "birth_date",
                                           "birth_city", "birth_country"))
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    for result in tool_results:
        visit(result.get("result"))
    # laureate details: awards live next to the laureate record
    for result in tool_results:
        data = (result.get("result") or {}).get("data") if isinstance(result.get("result"), dict) else None
        if isinstance(data, dict) and isinstance(data.get("laureate"), dict) and data["laureate"].get("evidence_id"):
            eid = data["laureate"]["evidence_id"]
            texts[eid] = texts.get(eid, "") + " " + " ".join(
                f"{a.get('year')} {a.get('category')} {a.get('motivation') or ''}" for a in data.get("awards", []))
    return texts


def _cited_units(answer: str) -> list[tuple[str, list[str], bool]]:
    """(claim, cited ids, inherited) per sentence.

    A citation-only fragment ("... relativity. [E1]") belongs to the previous
    sentence, and a citation ending a paragraph also covers that paragraph's
    otherwise uncited sentences (marked inherited) - a common answer style.
    """
    units: list[tuple[str, list[str], bool]] = []
    for paragraph in re.split(r"\n\s*\n", answer or ""):
        merged: list[str] = []
        for sentence in _sentences(paragraph):
            if merged and not _CITATION.sub("", sentence).strip(" .;,"):
                merged[-1] = merged[-1] + " " + sentence
            else:
                merged.append(sentence)
        parsed = []
        for sentence in merged:
            ids = sorted({i.upper() for group in _CITATION.findall(sentence) for i in re.findall(r"E\d+", group, re.I)})
            parsed.append((_CITATION.sub("", sentence).strip(), ids))
        # Only a citation that ENDS the paragraph covers the sentences before it;
        # text after the last citation stays uncited.
        last_ids = parsed[-1][1] if parsed and parsed[-1][1] else []
        for claim, ids in parsed:
            units.append((claim, ids or last_ids, not ids and bool(last_ids)))
    return units


def citation_support_review(answer: str, texts: dict[str, str]) -> dict[str, Any]:
    """Per sentence: cited ids, numbers and content terms absent from the cited evidence."""
    rows = []
    for claim, ids, inherited in _cited_units(answer):
        if not claim:
            continue
        if not ids:
            rows.append({"sentence": claim, "cited": [], "status": "uncited"})
            continue
        evidence = " ".join(texts.get(i, "") for i in ids)
        missing_numbers = sorted(_numbers(claim) - _numbers(evidence))
        terms = _content_terms(claim)
        missing_terms = sorted(t for t in terms if not _term_in(t, evidence.lower()))
        overlap = round(1 - len(missing_terms) / len(terms), 2) if terms else 1.0
        # Any unsupported number or content term needs a human look: a small
        # unsupported addition inside a mostly supported sentence is exactly
        # what an aggregate overlap ratio would hide.
        flagged = bool(missing_numbers) or bool(missing_terms) or not evidence.strip()
        rows.append({"sentence": claim, "cited": ids, "citation_inherited_from_paragraph": inherited,
                     "missing_numbers": missing_numbers, "terms_not_in_cited_evidence": missing_terms,
                     "term_overlap": overlap, "status": "review" if flagged else "lexically_supported"})
    flagged = [r for r in rows if r["status"] == "review"]
    return {"sentences": rows, "flagged": len(flagged),
            "note": "Lexical aid only; it cannot establish factual entailment. Manual evidence review is required."}
