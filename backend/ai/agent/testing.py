"""Deterministic tool-calling chat model for tests and offline evaluation.

``ScriptedChatModel`` implements the LangChain chat-model interface that
``create_agent`` needs (including ``bind_tools``), so tests exercise the real
agent loop: real tools, real ToolMessages, real middleware and budgets. Only
the model's *decisions* are scripted. Results obtained with it measure the
orchestration and validation code, NOT the quality of a real LLM.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

Policy = Callable[[list[BaseMessage], int], AIMessage]


class ScriptedChatModel(BaseChatModel):
    policy: Any
    calls: int = 0
    bound_tool_names: list[str] = Field(default_factory=list)
    transcripts: list[list[str]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted-tool-calling-fake"

    def bind_tools(self, tools, **kwargs):
        self.bound_tool_names = [getattr(t, "name", None) or t.get("name") for t in tools]
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self.transcripts.append([type(m).__name__ for m in messages])
        outcome = self.policy(list(messages), self.calls)
        self.calls += 1
        if isinstance(outcome, BaseException):
            raise outcome
        return ChatResult(generations=[ChatGeneration(message=outcome.model_copy(deep=True))])


# ---------------------------------------------------------------- message helpers

def tool_call(name: str, args: dict[str, Any], call_id: str) -> dict[str, Any]:
    return {"name": name, "args": args, "id": call_id, "type": "tool_call"}


def ai_tools(*calls: dict[str, Any], usage: dict[str, int] | None = None) -> AIMessage:
    return AIMessage(content="", tool_calls=list(calls), usage_metadata=usage)


def ai_text(text: str, usage: dict[str, int] | None = None) -> AIMessage:
    return AIMessage(content=text, usage_metadata=usage)


def script(*outcomes) -> Policy:
    """Return the outcomes in order (the last one repeats)."""
    def policy(messages, n):
        return outcomes[min(n, len(outcomes) - 1)]
    return policy


def tool_envelopes(messages: list[BaseMessage]) -> dict[str, dict[str, Any]]:
    """Parsed tool envelopes keyed by tool_call_id (non-JSON results are skipped)."""
    found = {}
    for message in messages:
        if isinstance(message, ToolMessage):
            try:
                found[message.tool_call_id] = json.loads(message.content)
            except (TypeError, ValueError):
                found[message.tool_call_id] = {"ok": False, "tool": message.name,
                                               "error": {"type": "non_json", "message": str(message.content)[:200]}}
    return found


# ---------------------------------------------------------------- answer composer

_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "what", "when", "where", "which", "who", "whom", "why", "how",
    "does", "did", "was", "were", "are", "is", "its", "into", "from", "their", "they", "them", "about", "explain",
    "nobel", "prize", "simple", "terms", "tell", "have", "has", "been",
}


def _content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in _STOPWORDS}


def query_excerpt(text: str, question: str, max_chars: int = 400, max_sentences: int = 2) -> str:
    """Pick the sentences of a retrieved chunk that best match the question.

    General rule (not tuned to any case): drop the chunk's "Title:" header line,
    rank sentences by content-word overlap with the question (earlier sentences
    win ties), keep the best ``max_sentences`` in document order, cap length.
    Falls back to the opening sentences when nothing overlaps.
    """
    body = text.split(":\n", 1)[1] if ":\n" in text[:200] else text
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", body) if s.strip()]
    if not sentences:
        return body[:max_chars]
    wanted = _content_words(question)
    ranked = sorted(range(len(sentences)), key=lambda i: (-len(_content_words(sentences[i]) & wanted), i))
    chosen = sorted(ranked[:max_sentences])
    return " ".join(sentences[i] for i in chosen)[:max_chars]


def _ids(items) -> str:
    ids = [i for i in items if i]
    return f" [{', '.join(ids)}]" if ids else ""


def compose_answer(envelopes: list[dict[str, Any]], question: str = "") -> str:
    """Deterministic, evidence-only answer used by the planned fake policy.

    Retrieved passages are quoted with ``query_excerpt`` (sentences most related
    to the question), not a fixed-length prefix.
    """
    lines: list[str] = []
    for env in envelopes:
        tool = env.get("tool")
        if not env.get("ok"):
            lines.append(f"The {tool} tool could not answer: {(env.get('error') or {}).get('message', 'error')}")
            continue
        data = env.get("data") or {}
        if tool == "search_laureates":
            laureates = data.get("laureates", [])
            if not laureates:
                lines.append(f"No matching laureates were found. {data.get('message') or ''}".strip())
            elif data.get("ambiguous_name"):
                names = "; ".join(f"{l['full_name']}{_ids([l.get('evidence_id')])}" for l in laureates)
                lines.append(f"Several laureates match: {names}. Which one do you mean?")
            else:
                parts = []
                for l in laureates:
                    award = (l.get("matched_awards") or l.get("other_awards") or [{}])[0]
                    parts.append(f"{l['full_name']} ({award.get('year')} {award.get('category')}: "
                                 f"{award.get('motivation')}){_ids([l.get('evidence_id')])}")
                lines.append("Laureates: " + "; ".join(parts) + ".")
        elif tool == "get_laureate_details":
            laureate = data.get("laureate", {})
            for award in data.get("awards", []):
                lines.append(f"{laureate.get('full_name')} received the {award['year']} {award['category']} prize "
                             f"{award.get('motivation')}{_ids([laureate.get('evidence_id')])}.")
            for c in data.get("contributions", []):
                significance = f" - {c['significance']}" if c.get("significance") else ""
                lines.append(f"Educational content: {c['title']}{significance}{_ids([c.get('evidence_id')])}")
                if c.get("explanation"):
                    e = c["explanation"]
                    lines.append(f"{e['level']} explanation (unverified educational content): "
                                 f"{query_excerpt(e['text'], question)}{_ids([e.get('evidence_id')])}")
            if not data.get("educational_content_available"):
                lines.append(data.get("message") or "No educational content is stored.")
        elif tool == "get_nobel_statistics":
            rows = data.get("result")
            shown = rows[:5] if isinstance(rows, list) else rows
            lines.append(f"{data.get('operation')} ({data.get('counting_unit')}): "
                         f"{json.dumps(shown, ensure_ascii=False)}{_ids([data.get('evidence_id')])}.")
        elif tool == "search_nobel_knowledge":
            strong = [r for r in data.get("results", []) if not r.get("weak_match")]
            if not strong:
                lines.append("The Nobel Explorer knowledge base does not contain relevant information for this question.")
            else:
                for r in strong[:2]:
                    note = " (unverified educational content)" if r["citation_status"] == "unverified_educational" else ""
                    lines.append(f"{r['title']}{note}: {query_excerpt(r['text'], question)}{_ids([r.get('evidence_id')])}")
    return "\n".join(lines) or "I could not find evidence to answer this question."


def _resolve_refs(args: dict[str, Any], outputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    from backend.ai.evaluation.run_tool_eval import _MISSING, resolve

    resolved = {}
    for key, value in args.items():
        if isinstance(value, dict) and "$ref" in value:
            value = resolve(outputs.get(value["$ref"], {}), value["path"])
            if value is _MISSING:
                value = None
        resolved[key] = value
    return resolved


def planned_policy(steps: list[list[dict[str, Any]]], *, compose: Callable = compose_answer,
                   usage: dict[str, int] | None = None, after_answer: str = "") -> Policy:
    """Emit each step's tool calls in turn, then an evidence-only answer.

    A step is a list of ``{"tool", "args"}``; arguments may reference earlier
    results with ``{"$ref": "<call id>", "path": "..."}`` where call ids are
    ``s<step>c<index>``. ``after_answer`` is appended verbatim (used by negative
    controls to inject fabricated citations or URLs).
    """
    usage = usage or {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    def policy(messages, n):
        outputs = tool_envelopes(messages)
        if n < len(steps):
            calls = [tool_call(spec["tool"], _resolve_refs(spec.get("args", {}), outputs), f"s{n}c{i}")
                     for i, spec in enumerate(steps[n])]
            return ai_tools(*calls, usage=usage)
        ordered = [outputs[cid] for cid in sorted(outputs, key=lambda c: (int(c[1:].split("c")[0]), int(c.split("c")[-1])))
                   if cid.startswith("s")]
        question = next((str(m.content) for m in messages if isinstance(m, HumanMessage)), "")
        return ai_text((compose(ordered, question) + after_answer).strip(), usage=usage)

    return policy
