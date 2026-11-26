"""Build or incrementally sync the Nobel knowledge vector index.

Usage (from the repository root, inside .venv-ai):

    python -m backend.ai.build_index            # incremental, idempotent sync
    python -m backend.ai.build_index --rebuild  # drop and recreate the collection
    python -m backend.ai.build_index --dry-run  # extract + chunk only, no writes

Database access is read-only. Credentials come from the usual DB_* variables
(``.env`` via python-dotenv, or the shell environment) and are never printed.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from backend.ai.chunking import chunk_documents
from backend.ai.config import ChunkingConfig, IndexConfig
from backend.ai.documents import build_all_documents, read_only_session


def _dir_size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def run(rebuild: bool = False, dry_run: bool = False, embedder=None,
        index_config: IndexConfig | None = None, chunk_config: ChunkingConfig | None = None,
        manifest_path: Path | None = None, documents=None) -> dict:
    index_config = index_config or IndexConfig()
    chunk_config = chunk_config or ChunkingConfig()
    if embedder is None:
        from backend.ai.embeddings import SentenceTransformerEmbedder
        embedder = SentenceTransformerEmbedder()

    timings: dict[str, float] = {}
    started = time.perf_counter()
    if documents is None:
        with read_only_session() as db:
            documents = build_all_documents(db)
    timings["extract_seconds"] = round(time.perf_counter() - started, 3)

    model_load = time.perf_counter()
    _ = embedder.dimension  # forces model load so chunk timing excludes it
    timings["model_load_seconds"] = round(time.perf_counter() - model_load, 3)
    started = time.perf_counter()
    chunks = chunk_documents(documents, embedder.count_tokens, chunk_config)
    timings["chunk_seconds"] = round(time.perf_counter() - started, 3)

    token_counts = [c.token_count for c in chunks]
    report: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "documents_by_type": dict(sorted(Counter(d.doc_type for d in documents).items())),
        "documents_total": len(documents),
        "chunks_by_type": dict(sorted(Counter(c.metadata["doc_type"] for c in chunks).items())),
        "chunks_total": len(chunks),
        "multi_chunk_documents": sorted({c.parent_doc_id for c in chunks if c.chunk_count > 1}),
        "chunk_tokens": {
            "max": max(token_counts, default=0),
            "mean": round(sum(token_counts) / len(token_counts), 1) if token_counts else 0,
            "limit": chunk_config.max_tokens,
        },
        "chunking": {
            "chunk_size_chars": chunk_config.chunk_size,
            "chunk_overlap_chars": chunk_config.chunk_overlap,
            "max_tokens": chunk_config.max_tokens,
        },
        "embedding": embedder.fingerprint(),
        "index": {
            "persist_dir": str(index_config.persist_dir),
            "collection": index_config.collection_name,
            "distance_space": index_config.distance_space,
        },
        "dry_run": dry_run,
    }

    if not dry_run:
        from backend.ai.vector_store import NobelVectorStore

        store = NobelVectorStore(embedder, index_config)
        if rebuild:
            store.reset_collection()
        result = store.sync(chunks)
        timings["embed_seconds"] = result.embed_seconds
        report["sync"] = result.__dict__

        # Persistence check: a brand-new client must see the same data.
        reopened = NobelVectorStore(embedder, index_config)
        report["reopened_count"] = reopened.count()
        report["reopened_distance_space"] = reopened.distance_space()
        if reopened.count() != len(chunks):
            raise RuntimeError(f"Reopened count {reopened.count()} != {len(chunks)} chunks")
        report["index_size_bytes"] = _dir_size(index_config.persist_dir)

    report["timings"] = timings
    manifest_path = manifest_path or index_config.persist_dir.parent / "index_manifest.json"
    if not dry_run:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        report["manifest_path"] = str(manifest_path)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rebuild", action="store_true", help="drop and recreate the collection")
    parser.add_argument("--dry-run", action="store_true", help="extract and chunk only; no index writes")
    args = parser.parse_args(argv)
    from sqlalchemy.exc import OperationalError

    from backend.ai.vector_store import EmbeddingModelMismatchError

    try:
        report = run(rebuild=args.rebuild, dry_run=args.dry_run)
    except OperationalError as error:
        # The driver message can contain the DB user name and host; print only the error code.
        code = error.orig.args[0] if getattr(error, "orig", None) and error.orig.args else "unknown"
        print(f"Database connection failed (MySQL error {code}). Check the DB_* settings.", file=sys.stderr)
        return 2
    except EmbeddingModelMismatchError as error:
        print(f"{error}", file=sys.stderr)
        return 3
    summary = {k: v for k, v in report.items() if k != "multi_chunk_documents"}
    summary["multi_chunk_documents"] = len(report["multi_chunk_documents"])
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
