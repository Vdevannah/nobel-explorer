"""Phase 2: validated, read-only tools combining structured and semantic retrieval.

Modules
-------
schemas         Pydantic argument schemas (single source of validation rules)
structured      search_laureates / get_laureate_details (existing services, ORM only)
statistics      get_nobel_statistics (allow-listed analytics aggregates)
semantic        search_nobel_knowledge wrapper (Phase 1 retrieval, compact output)
results         JSON envelopes and safe error translation
context         injectable read-only session factory and index provider
langchain_tools StructuredTool definitions
registry        exactly the four tools

No LLM is instantiated anywhere in this package.
"""

__all__ = ["TOOL_NAMES", "get_nobel_tools", "get_tool_registry"]


def __getattr__(name: str):
    # Lazy export: importing backend.ai.tools.schemas must not require LangChain.
    if name in __all__:
        from backend.ai.tools import registry

        return getattr(registry, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
