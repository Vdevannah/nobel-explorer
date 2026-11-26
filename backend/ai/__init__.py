"""AI Research Assistant retrieval foundation for Nobel Explorer.

Phase 1 scope: document preparation, chunking, local embeddings, a
persistent ChromaDB index and validated semantic retrieval. No LLM calls.

Heavy dependencies (sentence-transformers, chromadb) live in
``requirements-ai.txt`` and are imported lazily, so importing this package
never affects the existing FastAPI application.
"""
