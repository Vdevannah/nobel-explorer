"""Request-scoped agent middleware: evidence annotation, accounting and deadline.

LangChain's built-in ``ModelCallLimitMiddleware`` and ``ToolCallLimitMiddleware``
enforce the call budgets (tool calls are counted individually, including
parallel calls in one model response, and unknown-tool requests count too).
This middleware adds what they do not provide:

* annotates every tool result with evidence ids before the model reads it;
* records each tool execution (name, bounded arguments, ok/error, latency);
* counts real model calls, sums token usage and tags model-produced messages,
  so a synthetic "limit reached" message can be told apart from an answer;
* enforces a wall-clock deadline cooperatively: no new model call or tool
  execution starts after it (the service also applies a hard timeout).
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any

from langchain.agents.middleware import AgentMiddleware, hook_config
from langchain_core.messages import AIMessage, ToolMessage

from backend.ai.agent.evidence import EvidenceRegistry

DEADLINE_MESSAGE = "__nobel_agent_deadline_reached__"
UNKNOWN_TOOL_TEXT = "is not a valid tool"
MODEL_MESSAGE_PREFIX = "nobel-model-"


class AgentRunMiddleware(AgentMiddleware):
    def __init__(self, registry: EvidenceRegistry, deadline: float) -> None:
        super().__init__()
        self.registry = registry
        self.deadline = deadline
        self.model_calls = 0
        self.model_message_ids: set[str] = set()
        self.usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cached_input_tokens": 0}
        self.deadline_hit = False
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return "NobelAgentRunMiddleware"

    # ---------------------------------------------------------------- model side
    @hook_config(can_jump_to=["end"])
    def before_model(self, state, runtime) -> dict[str, Any] | None:
        if time.monotonic() >= self.deadline:
            self.deadline_hit = True
            return {"jump_to": "end", "messages": [AIMessage(content=DEADLINE_MESSAGE)]}
        return None

    @hook_config(can_jump_to=["end"])
    async def abefore_model(self, state, runtime) -> dict[str, Any] | None:
        return self.before_model(state, runtime)

    def _after_model_response(self, response):
        messages = getattr(response, "result", None) or ([response] if isinstance(response, AIMessage) else [])
        with self._lock:
            self.model_calls += 1
            for message in messages:
                if isinstance(message, AIMessage):
                    if not message.id:
                        message.id = f"{MODEL_MESSAGE_PREFIX}{self.model_calls}"
                    self.model_message_ids.add(message.id)
                    usage = message.usage_metadata or {}
                    for key in ("input_tokens", "output_tokens", "total_tokens"):
                        self.usage[key] += int(usage.get(key, 0) or 0)
                    details = usage.get("input_token_details") or {}
                    self.usage["cached_input_tokens"] += int(details.get("cache_read", 0) or 0)
        return response

    def wrap_model_call(self, request, handler):
        return self._after_model_response(handler(request))

    async def awrap_model_call(self, request, handler):
        return self._after_model_response(await handler(request))

    # ---------------------------------------------------------------- tool side
    def _deadline_message(self, request) -> ToolMessage:
        self.deadline_hit = True
        call = request.tool_call
        content = json.dumps({"tool": call.get("name"), "ok": False,
                              "error": {"type": "deadline_exceeded",
                                        "message": "The request time limit was reached; this tool call was not run."}})
        return ToolMessage(content=content, tool_call_id=call["id"], name=call.get("name"), status="error")

    def _process(self, request, message, started: float):
        call = request.tool_call
        latency = round((time.monotonic() - started) * 1000, 2)
        if not isinstance(message, ToolMessage):
            self.registry.record(call["id"], call.get("name", ""), call.get("args"), False, "unexpected_result", [], latency)
            return message
        content, ids, envelope = self.registry.annotate_content(call.get("name", ""), message.content)
        if envelope is not None:
            message.content = content
            ok = bool(envelope.get("ok"))
            error_type = None if ok else (envelope.get("error") or {}).get("type", "error")
        else:
            # Non-envelope results come from the agent runtime, not our tools
            # (e.g. "Error: <name> is not a valid tool"). Never echo them further.
            text = str(message.content or "")
            ok, error_type = False, ("unknown_tool" if UNKNOWN_TOOL_TEXT in text else "tool_error")
            self.registry.flag("tool_errors", f"{call.get('name')}: {error_type}")
        self.registry.record(call["id"], call.get("name", ""), call.get("args"), ok, error_type, ids, latency)
        return message

    def wrap_tool_call(self, request, handler):
        if time.monotonic() >= self.deadline:
            return self._process(request, self._deadline_message(request), time.monotonic())
        started = time.monotonic()
        return self._process(request, handler(request), started)

    async def awrap_tool_call(self, request, handler):
        if time.monotonic() >= self.deadline:
            return self._process(request, self._deadline_message(request), time.monotonic())
        started = time.monotonic()
        return self._process(request, await handler(request), started)
