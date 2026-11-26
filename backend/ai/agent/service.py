"""Run the Nobel research agent for one question and build a validated response.

One agent is built per request (about 1 ms), so no state, evidence or
counters are shared between requests. The four Phase 2 tools are reused from
the registry unchanged; nothing here defines or duplicates a tool.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from backend.ai.agent.config import AgentConfig
from backend.ai.agent.evidence import EvidenceRegistry, _bounded_args, validate_answer
from backend.ai.agent.middleware import DEADLINE_MESSAGE, AgentRunMiddleware
from backend.ai.agent.prompts import SYSTEM_PROMPT
from backend.ai.agent.schemas import ChatResponse, ErrorInfo, ToolCallSummary, Usage
from backend.ai.tools.context import ToolContext
from backend.ai.tools.registry import get_nobel_tools

logger = logging.getLogger(__name__)

MAX_ANSWER_CHARS = 6000
TOOL_LIMIT_TEXT = "Tool call limit exceeded"
UNKNOWN_TOOL_TEXT = "is not a valid tool"

LIMITATION_TEXT = {
    "weak_semantic_evidence": "Semantic search returned only weak matches (similarity below the provisional 0.40 "
                              "threshold) for: {}. Treat this as insufficient evidence.",
    "ambiguous_name": "A name matched several laureates ({}); the answer may need clarification.",
    "empty_results": "No matching records: {}.",
    "truncated": "Results were truncated: {}.",
    "missing_educational_content": "No educational explanations are stored for {}.",
    "tool_errors": "Some tool calls failed: {}.",
}


class AgentInputError(ValueError):
    """The question violates the configured input limits."""


def build_chat_model(config: AgentConfig, *, http_client=None, http_async_client=None):
    """Create the OpenAI chat model. Construction makes no network request.

    * ``use_responses_api=False``: langchain-openai 1.8.5 silently switches
      ``gpt-6*`` models to the Responses API when tools are bound. We pin
      Chat Completions, the message format the agent is built and tested on.
    * ``reasoning_effort="none"``: gpt-6-luna supports function calling on Chat
      Completions only with reasoning effort ``none`` (OpenAI model page).
    * ``max_tokens`` is sent as ``max_completion_tokens`` by langchain-openai.
    * ``temperature`` is sent only when configured (support is undocumented).
    * ``http_client`` / ``http_async_client`` let tests mock the transport.
    """
    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {
        "model": config.model,
        "api_key": config.openai_api_key,
        "timeout": config.provider_timeout_seconds,
        "max_retries": config.provider_max_retries,
        "max_tokens": config.max_output_tokens,
        "use_responses_api": False,
    }
    if config.reasoning_effort is not None:
        kwargs["reasoning_effort"] = config.reasoning_effort
    if config.temperature is not None:
        kwargs["temperature"] = config.temperature
    if http_client is not None:
        kwargs["http_client"] = http_client
    if http_async_client is not None:
        kwargs["http_async_client"] = http_async_client
    return ChatOpenAI(**kwargs)


def build_agent(chat_model, tools, middleware: list) -> Any:
    return create_agent(chat_model, tools, system_prompt=SYSTEM_PROMPT, middleware=middleware)


def _provider_error(exc: BaseException) -> ErrorInfo:
    """Map provider/application errors to fixed, credential-free messages.

    langchain-openai re-raises SDK errors as its own subclasses (for example
    ``OpenAITimeoutError`` subclasses ``openai.APITimeoutError``), so the checks
    use ``isinstance`` in most-specific-first order, never class names.
    Provider messages are never copied: some include part of the API key.
    """
    try:
        import openai
    except ImportError:  # pragma: no cover - AI packages always present here
        openai = None
    if openai is not None:
        ordered = [
            (openai.APITimeoutError, "provider_timeout", "The language model did not respond in time."),
            (openai.APIConnectionError, "provider_unavailable", "The language model provider could not be reached."),
            (openai.RateLimitError, "provider_rate_limited", "The language model provider is rate limiting requests."),
            (openai.AuthenticationError, "provider_auth", "The language model provider rejected the credentials."),
            (openai.PermissionDeniedError, "provider_auth", "The language model provider denied access."),
            (openai.NotFoundError, "provider_model_not_found",
             "The configured model is not available to this API key (check OPENAI_MODEL)."),
            (openai.BadRequestError, "provider_bad_request", "The language model provider rejected the request."),
            (openai.APIError, "provider_error", "The language model provider returned an error."),
        ]
        for cls, kind, message in ordered:
            if isinstance(exc, cls):
                return ErrorInfo(type=kind, message=message)
    if type(exc).__name__ == "OpenAIRefusalError":
        return ErrorInfo(type="provider_refusal", message="The language model refused to answer.")
    if isinstance(exc, TimeoutError):
        return ErrorInfo(type="provider_timeout", message="The language model did not respond in time.")
    return ErrorInfo(type="internal_error", message=f"The assistant failed unexpectedly ({type(exc).__name__}).")


def _answer_text(message: AIMessage) -> str:
    content = message.content
    if isinstance(content, list):
        content = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
    return str(content or "").strip()


def _recorded_summaries(registry: EvidenceRegistry) -> list[ToolCallSummary]:
    """Tools that actually executed, for responses produced without final messages."""
    return [ToolCallSummary(id=r.tool_call_id, name=r.name, arguments=r.arguments, ok=r.ok,
                            error_type=r.error_type, evidence_ids=r.evidence_ids, latency_ms=r.latency_ms)
            for r in registry.records.values()]


def _tool_summaries(messages: list, registry: EvidenceRegistry) -> list[ToolCallSummary]:
    results = {m.tool_call_id: m for m in messages if isinstance(m, ToolMessage)}
    summaries = []
    for message in messages:
        if not isinstance(message, AIMessage):
            continue
        for call in message.tool_calls or []:
            record = registry.records.get(call["id"])
            if record is not None:
                summaries.append(ToolCallSummary(id=record.tool_call_id, name=record.name, arguments=record.arguments,
                                                 ok=record.ok, error_type=record.error_type,
                                                 evidence_ids=record.evidence_ids, latency_ms=record.latency_ms))
                continue
            # Not executed through the tool node: blocked by the budget or unknown tool.
            result = results.get(call["id"])
            text = str(getattr(result, "content", "") or "")
            if TOOL_LIMIT_TEXT in text or "Execution stopped" in text:
                error_type = "tool_budget_exceeded"
            elif UNKNOWN_TOOL_TEXT in text:
                error_type = "unknown_tool"
            else:
                error_type = "not_executed"
            registry.flag("tool_errors", f"{call.get('name')}: {error_type}")
            summaries.append(ToolCallSummary(id=call["id"], name=str(call.get("name"))[:80],
                                             arguments=_bounded_args(call.get("args")), ok=False, error_type=error_type))
    return summaries


def _limitations(registry: EvidenceRegistry, citations: list, check, grounding: str | None) -> list[str]:
    notes = [LIMITATION_TEXT[key].format("; ".join(values)) for key, values in registry.flags.items()
             if key in LIMITATION_TEXT]
    if any(c.citation_status == "unverified_educational" for c in citations):
        notes.append("Cited explanations are unverified educational content without stored citations; "
                     "related sources are context only.")
    if check is not None:
        if check.fabricated_ids:
            notes.append(f"Removed citation references not backed by tool evidence: {', '.join(check.fabricated_ids)}. "
                         "Statements marked [unverified] are not supported by retrieved evidence.")
        if check.removed_urls:
            notes.append(f"Removed {len(check.removed_urls)} URL(s) that no tool returned (shown as [link removed]).")
        if check.related_source_urls_removed:
            notes.append("Removed related-source URL(s) presented as citations; they are context only.")
    if grounding == "no_evidence":
        notes.append("No tool evidence was retrieved; the answer is not grounded in Nobel Explorer data.")
    elif grounding == "uncited":
        notes.append("The answer does not cite any retrieved evidence.")
    return notes


async def run_agent(
    question: str,
    *,
    config: AgentConfig,
    chat_model=None,
    tool_context: ToolContext | None = None,
    request_id: str | None = None,
    capture: dict | None = None,
) -> ChatResponse:
    """Answer one question. Never raises for model/tool/budget failures.

    ``capture`` (internal, for evaluation and traces only; never exposed by the API)
    receives the final message list, the evidence registry and the citation check.
    """
    started = time.monotonic()
    request_id = request_id or uuid.uuid4().hex
    question = " ".join(str(question).split())
    if not question or len(question) > config.max_question_chars:
        raise AgentInputError(f"question must be 1-{config.max_question_chars} characters")

    def respond(status: str, **fields: Any) -> ChatResponse:
        response = ChatResponse(request_id=request_id, status=status, model=config.model,
                                latency_ms=round((time.monotonic() - started) * 1000, 1), **fields)
        logger.info("agent request %s status=%s model_calls=%s tool_calls=%s latency_ms=%s",
                    request_id, status, response.model_calls, len(response.tool_calls), response.latency_ms)
        return response

    if chat_model is None:
        available, reason = config.availability()
        if not available:
            return respond("unavailable", error=ErrorInfo(type="unavailable", message=reason))
        chat_model = build_chat_model(config)

    registry = EvidenceRegistry()
    run = AgentRunMiddleware(registry, deadline=started + config.max_duration_seconds)
    if capture is not None:
        # Exposed from the start so evaluation keeps the evidence even if the run
        # later fails, times out or exhausts its budget.
        capture.update(registry=registry, middleware=run)
    agent = build_agent(chat_model, get_nobel_tools(tool_context), middleware=[
        run,
        ModelCallLimitMiddleware(run_limit=config.max_model_calls, exit_behavior="end"),
        ToolCallLimitMiddleware(run_limit=config.max_tool_calls, exit_behavior="continue"),
    ])

    def usage() -> Usage | None:
        return Usage(**run.usage) if any(run.usage.values()) else None

    try:
        state = await asyncio.wait_for(
            agent.ainvoke({"messages": [HumanMessage(content=question)]},
                          config={"recursion_limit": config.recursion_limit}),
            timeout=config.max_duration_seconds,
        )
    except asyncio.TimeoutError:
        return respond("timeout", answer="I could not finish within the time limit. Please try a narrower question.",
                       tool_calls=_recorded_summaries(registry), model_calls=run.model_calls, usage=usage(),
                       evidence_limitations=["The request time limit was reached before an answer was produced."],
                       error=ErrorInfo(type="timeout", message="The request exceeded the configured time limit."))
    except Exception as exc:  # noqa: BLE001 - every failure becomes a controlled response
        if type(exc).__name__ == "GraphRecursionError":
            return respond("budget_exhausted", model_calls=run.model_calls, usage=usage(),
                           tool_calls=_recorded_summaries(registry),
                           answer="I could not complete this request within the configured step limit.",
                           error=ErrorInfo(type="step_limit", message="The agent step limit was reached."))
        error = _provider_error(exc)
        logger.warning("agent request %s failed: %s (%s)", request_id, error.type, type(exc).__name__)
        return respond("error", model_calls=run.model_calls, usage=usage(), error=error,
                       tool_calls=_recorded_summaries(registry))

    messages = state["messages"]
    if capture is not None:
        capture.update(messages=messages, registry=registry)
    tool_calls = _tool_summaries(messages, registry)
    final = next((m for m in reversed(messages) if isinstance(m, AIMessage)), None)
    genuine = final is not None and final.id in run.model_message_ids and not final.tool_calls

    if not genuine:
        reason = "time limit" if run.deadline_hit or (final and final.content == DEADLINE_MESSAGE) else "model-call limit"
        status = "timeout" if reason == "time limit" else "budget_exhausted"
        return respond(status, answer=f"I could not complete this request within the configured {reason}. "
                                      "Please try a narrower question.",
                       tool_calls=tool_calls, model_calls=run.model_calls, usage=usage(),
                       evidence_limitations=_limitations(registry, [], None, None) +
                       [f"The {reason} was reached before a final answer was produced."],
                       error=ErrorInfo(type="deadline_exceeded" if status == "timeout" else "model_call_limit",
                                       message=f"The configured {reason} was reached."))

    check = validate_answer(_answer_text(final)[:MAX_ANSWER_CHARS], registry)
    if capture is not None:
        capture["citation_check"] = check
    tampered = bool(check.fabricated_ids or check.removed_urls or check.related_source_urls_removed)
    if not registry.items:
        grounding = "no_evidence"
    elif check.citations:
        grounding = "partially_cited" if tampered else "cited"
    else:
        grounding = "uncited"
    if any(s.error_type == "tool_budget_exceeded" for s in tool_calls):
        registry.flag("tool_errors", "tool-call budget reached; some requested calls were not executed")
    return respond("completed", answer=check.answer, grounding=grounding, citations=check.citations,
                   tool_calls=tool_calls, model_calls=run.model_calls, usage=usage(),
                   evidence_limitations=_limitations(registry, check.citations, check, grounding))


def run_agent_sync(question: str, **kwargs: Any) -> ChatResponse:
    return asyncio.run(run_agent(question, **kwargs))
