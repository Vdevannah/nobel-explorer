"""LangChain tool definitions for the four Nobel tools.

Each tool is a ``StructuredTool`` with:
* a stable ``name`` and a description that says WHEN to use it,
* an explicit Pydantic ``args_schema`` (LangChain derives the JSON schema),
* argument validation errors returned as the same JSON error envelope as
  runtime errors (``handle_validation_error``), never raised to the caller,
* bounded, JSON-serialisable output.

The plain ``*_tool_function`` callables can be used without LangChain or an
LLM; the tools themselves can be invoked directly with ``tool.invoke({...})``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ValidationError

from backend.ai.tools.context import ToolContext
from backend.ai.tools.results import error, format_validation_error, run_safely
from backend.ai.tools.schemas import (
    KnowledgeSearchInput,
    LaureateDetailsInput,
    NobelStatisticsInput,
    SearchLaureatesInput,
)
from backend.ai.tools.semantic import search_knowledge
from backend.ai.tools.statistics import get_nobel_statistics
from backend.ai.tools.structured import get_laureate_details, search_laureates

SEARCH_LAUREATES = "search_laureates"
GET_LAUREATE_DETAILS = "get_laureate_details"
GET_NOBEL_STATISTICS = "get_nobel_statistics"
SEARCH_NOBEL_KNOWLEDGE = "search_nobel_knowledge"

DESCRIPTIONS = {
    SEARCH_LAUREATES: (
        "Find Nobel laureates by exact structured filters: award year, category, birth country, gender "
        "and/or part of the name. Use this for factual 'who won' questions (e.g. 'Who won the 2022 Nobel "
        "Prize in Chemistry?') and to obtain laureate_id values for get_laureate_details. Returns matching "
        "laureates with their matching awards and prize motivations. Does not search explanations."
    ),
    GET_LAUREATE_DETAILS: (
        "Use this after search_laureates, once you know a single laureate_id, to answer questions about one "
        "laureate. Returns the stored record for that laureate: birth information, "
        "every award with year, category, motivation and award-time affiliations, plus any educational "
        "contributions, available explanation levels and source-linked connections. Optionally include the "
        "full explanation at one level. Does not invent biographies when no educational content exists."
    ),
    GET_NOBEL_STATISTICS: (
        "Compute an allow-listed aggregate over the Nobel database (counts by category, gender, decade, "
        "birth country, era or award-time institution; summary totals; average age at award). Use this for "
        "'how many' and trend questions. Each result states exactly what is counted (distinct laureates, "
        "prizes, or awards) and the filters applied. Arbitrary queries are not supported."
    ),
    SEARCH_NOBEL_KNOWLEDGE: (
        "Semantic search over Nobel Explorer's knowledge base: laureate records, prize motivations, and "
        "educational explanations of the photoelectric effect, general relativity, mRNA vaccines and click "
        "chemistry at four levels (Simple, Explore, Advanced, Expert), plus their applications. Use this for "
        "'explain', 'how' and 'why' questions. Results are nearest neighbours with similarity scores and a "
        "weak_match flag; they may be irrelevant, so check them before relying on them. Not suitable for "
        "exact year/category lookups (use search_laureates)."
    ),
}


def _bind(
    name: str,
    schema: type[BaseModel],
    core: Callable[[BaseModel], dict[str, Any]],
) -> Callable[..., dict[str, Any]]:
    def tool_function(**kwargs: Any) -> dict[str, Any]:
        return run_safely(name, lambda: core(schema.model_validate(kwargs)))

    tool_function.__name__ = f"{name}_tool_function"
    return tool_function


def _validation_handler(name: str) -> Callable[[ValidationError], dict[str, Any]]:
    def handle(exc: ValidationError) -> dict[str, Any]:
        return error(name, "validation_error", format_validation_error(exc))

    return handle


def build_tool_functions(context: ToolContext | None = None) -> dict[str, Callable[..., dict[str, Any]]]:
    """Plain callables (no LangChain needed), keyed by tool name."""
    ctx = context or ToolContext()

    def with_session(func):
        def call(params):
            with ctx.session_factory() as db:
                return func(params, db)
        return call

    return {
        SEARCH_LAUREATES: _bind(SEARCH_LAUREATES, SearchLaureatesInput, with_session(search_laureates)),
        GET_LAUREATE_DETAILS: _bind(GET_LAUREATE_DETAILS, LaureateDetailsInput, with_session(get_laureate_details)),
        GET_NOBEL_STATISTICS: _bind(GET_NOBEL_STATISTICS, NobelStatisticsInput, with_session(get_nobel_statistics)),
        SEARCH_NOBEL_KNOWLEDGE: _bind(
            SEARCH_NOBEL_KNOWLEDGE, KnowledgeSearchInput,
            lambda params: search_knowledge(params, ctx.store_provider()),
        ),
    }


_SCHEMAS = {
    SEARCH_LAUREATES: SearchLaureatesInput,
    GET_LAUREATE_DETAILS: LaureateDetailsInput,
    GET_NOBEL_STATISTICS: NobelStatisticsInput,
    SEARCH_NOBEL_KNOWLEDGE: KnowledgeSearchInput,
}


def build_nobel_tools(context: ToolContext | None = None) -> list[StructuredTool]:
    functions = build_tool_functions(context)
    return [
        StructuredTool.from_function(
            func=functions[name],
            name=name,
            description=DESCRIPTIONS[name],
            args_schema=_SCHEMAS[name],
            infer_schema=False,
            handle_validation_error=_validation_handler(name),
        )
        for name in (SEARCH_LAUREATES, GET_LAUREATE_DETAILS, GET_NOBEL_STATISTICS, SEARCH_NOBEL_KNOWLEDGE)
    ]
