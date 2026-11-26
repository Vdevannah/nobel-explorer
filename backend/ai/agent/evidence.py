"""Evidence collection and citation validation.

Tool results are annotated with request-scoped evidence ids (E1, E2, ...)
BEFORE the model sees them. The final answer may cite only those ids; after
the run, every citation and every URL in the answer is checked against the
evidence that tools actually returned.

Provenance is preserved exactly:
* source_linked          -> ``source`` (direct citation) may be shown
* structured_record      -> ``source_name`` only; no URL exists
* unverified_educational -> ``related_source`` is CONTEXT ONLY and is never
                            promoted to a citation, and its URL may not be
                            presented as a source in the answer
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass, field
from typing import Any

from backend.ai.agent.schemas import Citation, SourceRef

CITE_GROUP = re.compile(r"\[\s*(E\d+(?:\s*[,;]\s*E\d+)*)\s*\]", re.IGNORECASE)
# Any markdown link, whatever its scheme (javascript:, data:, http:, ...).
MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\(\s*<?((?:[^()\s<>]|\([^()\s]*\))+)>?\s*\)")
BARE_URL = re.compile(r"https?://[^\s\)\]<>\"']+", re.IGNORECASE)
WWW_HOST = re.compile(r"(?<![/@\w.])www\.[a-z0-9-]+(?:\.[a-z0-9-]+)+[^\s\)\]<>\"']*", re.IGNORECASE)
UNVERIFIED_MARK = "[unverified]"
LINK_REMOVED_MARK = "[link removed]"
MAX_ARG_CHARS = 200


@dataclass
class EvidenceItem:
    evidence_id: str
    tool: str
    kind: str
    title: str
    citation_status: str
    source: dict[str, str] | None = None
    source_name: str | None = None
    related_source: dict[str, str] | None = None
    reference: dict[str, Any] = field(default_factory=dict)

    def to_citation(self) -> Citation:
        return Citation(
            evidence_id=self.evidence_id,
            tool=self.tool,
            kind=self.kind,
            title=self.title,
            citation_status=self.citation_status,
            source=SourceRef(**self.source) if self.source else None,
            source_name=self.source_name,
            related_source=SourceRef(**self.related_source) if self.related_source else None,
            reference=self.reference,
        )


@dataclass
class ToolRecord:
    tool_call_id: str
    name: str
    arguments: dict[str, Any]
    ok: bool
    error_type: str | None
    evidence_ids: list[str]
    latency_ms: float | None


def _bounded_args(args: Any) -> dict[str, Any]:
    if not isinstance(args, dict):
        return {}
    clean: dict[str, Any] = {}
    for key, value in list(args.items())[:12]:
        if isinstance(value, str) and len(value) > MAX_ARG_CHARS:
            value = value[:MAX_ARG_CHARS] + "…"
        elif not isinstance(value, (str, int, float, bool, type(None))):
            value = str(value)[:MAX_ARG_CHARS]
        clean[str(key)[:60]] = value
    return clean


class EvidenceRegistry:
    """Request-scoped store of evidence items and tool execution records."""

    def __init__(self) -> None:
        self._lock = threading.Lock()  # parallel tool calls may run in threads
        self._counter = 0
        self.items: dict[str, EvidenceItem] = {}
        self.records: dict[str, ToolRecord] = {}
        self.flags: dict[str, list[str]] = {}

    # ---------------------------------------------------------------- ids
    def _new(self, tool: str, kind: str, title: str, citation_status: str, **extra: Any) -> str:
        with self._lock:
            self._counter += 1
            evidence_id = f"E{self._counter}"
            self.items[evidence_id] = EvidenceItem(evidence_id, tool, kind, str(title)[:200], citation_status, **extra)
        return evidence_id

    def flag(self, kind: str, detail: str) -> None:
        with self._lock:
            values = self.flags.setdefault(kind, [])
            if detail not in values:
                values.append(detail)

    # ---------------------------------------------------------------- annotation
    def annotate(self, tool: str, envelope: dict[str, Any]) -> list[str]:
        """Attach evidence ids to citable parts of a tool envelope (in place)."""
        if not envelope.get("ok"):
            error = envelope.get("error") or {}
            self.flag("tool_errors", f"{tool}: {error.get('type', 'error')}")
            return []
        data = envelope.get("data") or {}
        ids: list[str] = []
        if tool == "search_laureates":
            provenance = data.get("provenance") or {}
            for laureate in data.get("laureates", []):
                laureate["evidence_id"] = self._new(
                    tool, "laureate_record", laureate.get("full_name", ""), "structured_record",
                    source_name=provenance.get("source_name"),
                    reference={"laureate_id": laureate.get("laureate_id"),
                               "nobel_laureate_id": laureate.get("nobel_laureate_id")},
                )
                ids.append(laureate["evidence_id"])
            if data.get("ambiguous_name"):
                self.flag("ambiguous_name", f"'{data.get('filters', {}).get('name')}' matched {data.get('total_matches')} laureates")
            if data.get("total_matches") == 0:
                self.flag("empty_results", "search_laureates found no matching laureates")
            if data.get("truncated"):
                self.flag("truncated", f"search_laureates returned {data.get('returned')} of {data.get('total_matches')} matches")
        elif tool == "get_laureate_details":
            laureate = data.get("laureate") or {}
            provenance = data.get("provenance") or {}
            laureate["evidence_id"] = self._new(
                tool, "laureate_record", laureate.get("full_name", ""), "structured_record",
                source_name=provenance.get("source_name"), reference={"laureate_id": laureate.get("laureate_id")},
            )
            ids.append(laureate["evidence_id"])
            for contribution in data.get("contributions", []):
                contribution["evidence_id"] = self._new(
                    tool, "contribution", contribution.get("title", ""), contribution.get("citation_status", ""),
                    source=contribution.get("source"), reference={"contribution_id": contribution.get("contribution_id")},
                )
                ids.append(contribution["evidence_id"])
                explanation = contribution.get("explanation")
                if explanation:
                    explanation["evidence_id"] = self._new(
                        tool, "explanation", f"{contribution.get('title', '')} - {explanation.get('level')} explanation",
                        "unverified_educational", related_source=explanation.get("related_source"),
                        reference={"contribution_id": contribution.get("contribution_id"), "level": explanation.get("level")},
                    )
                    ids.append(explanation["evidence_id"])
                for connection in contribution.get("connections", []):
                    connection["evidence_id"] = self._new(
                        tool, "connection", connection.get("title", ""), connection.get("citation_status", ""),
                        source=connection.get("source"), reference={"connection_id": connection.get("connection_id")},
                    )
                    ids.append(connection["evidence_id"])
            if not data.get("educational_content_available"):
                self.flag("missing_educational_content", laureate.get("full_name", "this laureate"))
        elif tool == "get_nobel_statistics":
            data["evidence_id"] = self._new(
                tool, "statistic", data.get("operation", "statistic"), "structured_record",
                source_name=data.get("source"),
                reference={"operation": data.get("operation"), "applied_filters": data.get("applied_filters", {}),
                           "counting_unit": data.get("counting_unit")},
            )
            ids.append(data["evidence_id"])
            if data.get("empty"):
                self.flag("empty_results", f"get_nobel_statistics({data.get('operation')}) returned no data")
        elif tool == "search_nobel_knowledge":
            for result in data.get("results", []):
                result["evidence_id"] = self._new(
                    tool, f"knowledge:{result.get('doc_type', 'document')}", result.get("title", ""),
                    result.get("citation_status", ""), source=result.get("source"),
                    related_source=result.get("related_source"),
                    reference={"doc_id": result.get("doc_id"), "chunk_id": result.get("chunk_id"),
                               "similarity": result.get("similarity"), "weak_match": result.get("weak_match")},
                )
                ids.append(result["evidence_id"])
            if data.get("all_results_weak"):
                self.flag("weak_semantic_evidence", data.get("query", ""))
            if not data.get("results"):
                self.flag("empty_results", "search_nobel_knowledge returned no results")
        envelope["evidence_ids"] = ids
        if ids:
            envelope["citation_instruction"] = "Cite supported claims with these evidence ids in square brackets, e.g. [" + ids[0] + "]."
        return ids

    def annotate_content(self, tool: str, content: Any) -> tuple[Any, list[str], dict[str, Any] | None]:
        """Annotate a ToolMessage content string; non-envelope content is returned unchanged."""
        if not isinstance(content, str):
            return content, [], None
        try:
            envelope = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            return content, [], None
        if not isinstance(envelope, dict) or "ok" not in envelope or "tool" not in envelope:
            return content, [], None
        ids = self.annotate(tool, envelope)
        return json.dumps(envelope, ensure_ascii=False), ids, envelope

    def record(self, tool_call_id: str, name: str, arguments: Any, ok: bool, error_type: str | None,
               evidence_ids: list[str], latency_ms: float | None) -> None:
        with self._lock:
            self.records[tool_call_id] = ToolRecord(tool_call_id, name, _bounded_args(arguments), ok, error_type,
                                                    evidence_ids, latency_ms)

    # ---------------------------------------------------------------- validation
    def direct_source_urls(self) -> set[str]:
        return {i.source["url"] for i in self.items.values() if i.source and i.source.get("url")}

    def related_source_urls(self) -> set[str]:
        return {i.related_source["url"] for i in self.items.values() if i.related_source and i.related_source.get("url")}


@dataclass
class CitationCheck:
    answer: str
    citations: list[Citation]
    fabricated_ids: list[str]
    removed_urls: list[str]
    related_source_urls_removed: list[str]


def _strip_url(url: str) -> str:
    return url.rstrip(".,;:!?")


def validate_answer(answer: str, registry: EvidenceRegistry) -> CitationCheck:
    """Keep only citations and URLs that tools actually returned.

    * Citation ids are matched case-insensitively. An id the request never
      issued is replaced by ``[unverified]`` so the claim it was attached to is
      visibly unsupported instead of silently losing its citation.
    * Only exact ``source.url`` values of returned evidence may appear as links.
      Every other URL (other hosts, look-alike domains, extra query strings,
      ``related_source`` URLs, ``javascript:``/``data:`` links, bare ``www.``
      hosts) is replaced by ``[link removed]`` (markdown links keep their label).
    """
    cited: list[str] = []
    fabricated: list[str] = []

    def replace_group(match: re.Match) -> str:
        ids = [part.strip().upper() for part in re.split(r"[,;]", match.group(1))]
        valid = []
        for i in ids:
            if i in registry.items:
                valid.append(i)
                if i not in cited:
                    cited.append(i)
            elif i not in fabricated:
                fabricated.append(i)
        return f"[{', '.join(valid)}]" if valid else UNVERIFIED_MARK

    text = CITE_GROUP.sub(replace_group, answer)

    direct = registry.direct_source_urls()
    related = registry.related_source_urls() - direct
    removed: list[str] = []
    related_removed: list[str] = []

    def allowed(url: str) -> bool:
        """True only for an exact direct source URL; records everything else once."""
        clean = _strip_url(url)
        if clean.lower().startswith(("http://", "https://")) and clean in direct:
            return True
        (related_removed if clean in related else removed).append(clean)
        return False

    def markdown(match: re.Match) -> str:
        label, target = match.group(1), match.group(2)
        return match.group(0) if allowed(target) else label  # keep the label, drop the target

    text = MARKDOWN_LINK.sub(markdown, text)

    def bare(match: re.Match) -> str:
        url = match.group(0)
        clean = _strip_url(url)
        return url if allowed(url) else LINK_REMOVED_MARK + url[len(clean):]

    text = BARE_URL.sub(bare, text)

    def www(match: re.Match) -> str:
        token = match.group(0)
        clean = _strip_url(token)
        if any(u.split("://", 1)[-1] == clean for u in direct):
            return token
        removed.append(clean)
        return LINK_REMOVED_MARK + token[len(clean):]

    text = WWW_HOST.sub(www, text)
    text = text.replace("<" + LINK_REMOVED_MARK + ">", LINK_REMOVED_MARK)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" +([.,;:])", r"\1", text).strip()
    citations = [registry.items[i].to_citation() for i in cited]
    return CitationCheck(text, citations, fabricated, sorted(set(removed)), sorted(set(related_removed)))
