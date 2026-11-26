"""Registry of exactly the four Nobel tools intended for the Phase 3 agent."""

from __future__ import annotations

from langchain_core.tools import StructuredTool

from backend.ai.tools.context import ToolContext
from backend.ai.tools.langchain_tools import (
    GET_LAUREATE_DETAILS,
    GET_NOBEL_STATISTICS,
    SEARCH_LAUREATES,
    SEARCH_NOBEL_KNOWLEDGE,
    build_nobel_tools,
)

TOOL_NAMES: tuple[str, ...] = (
    SEARCH_LAUREATES,
    GET_LAUREATE_DETAILS,
    GET_NOBEL_STATISTICS,
    SEARCH_NOBEL_KNOWLEDGE,
)


def get_tool_registry(context: ToolContext | None = None) -> dict[str, StructuredTool]:
    tools = build_nobel_tools(context)
    registry = {t.name: t for t in tools}
    if tuple(registry) != TOOL_NAMES:
        raise RuntimeError(f"Tool registry mismatch: {tuple(registry)} != {TOOL_NAMES}")
    return registry


def get_nobel_tools(context: ToolContext | None = None) -> list[StructuredTool]:
    return list(get_tool_registry(context).values())
