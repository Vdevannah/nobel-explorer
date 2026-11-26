"""Phase 3: LangChain research agent over the four Phase 2 tools.

Modules
-------
config      environment-driven, validated settings (Pydantic only)
schemas     API request/response models (Pydantic only)
prompts     system prompt
evidence    evidence ids, citation and URL validation
middleware  per-request accounting, evidence annotation and deadline
service     builds and runs the agent (imports LangChain)
testing     deterministic tool-calling fake chat model (tests and offline evaluation)

``config`` and ``schemas`` import without LangChain, so the API can report
"unavailable" in an environment without AI packages.
"""
