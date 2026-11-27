"""Read-only check that a packaged knowledge index matches a database.

    python -m backend.ai.check_index_consistency [--index-dir PATH] [--json]

The index refers to database records by internal ids (for example
``laureate_ids``), and every chunk stores a content hash that covers its text
and that metadata. This tool rebuilds the chunk list from the database exactly as
the index builder does (same extraction, chunking and tokenizer, no embedding)
and compares chunk ids and content hashes with the index.

Safety:
* Database access uses ``read_only_session`` (a dedicated engine with
  ``SET SESSION TRANSACTION READ ONLY``); nothing is written.
* The index is opened from a temporary COPY, so the packaged files are never
  modified. Only ids and counts are printed: no record text, no credentials.

Exit code 0: identical. 1: differences found (rebuild the index from that
database before deploying). 2: the check could not run.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

from backend.ai.config import ChunkingConfig, IndexConfig

MAX_LISTED = 20


def _index_hashes(index_dir: Path, collection_name: str) -> dict[str, str]:
    import chromadb
    from chromadb.config import Settings

    with tempfile.TemporaryDirectory(prefix="index-check-") as tmp:
        copy = Path(tmp) / "chroma"
        shutil.copytree(index_dir, copy)
        client = chromadb.PersistentClient(path=str(copy), settings=Settings(anonymized_telemetry=False))
        records = client.get_collection(collection_name, embedding_function=None).get(include=["metadatas"])
        hashes = {chunk_id: (meta or {}).get("content_hash", "") for chunk_id, meta in
                  zip(records["ids"], records["metadatas"])}
        del client
    return hashes


def check(index_dir: Path | None = None, *, documents=None, embedder=None,
          collection_name: str | None = None, chunk_config: ChunkingConfig | None = None) -> dict:
    from backend.ai.chunking import chunk_documents

    index_config = IndexConfig()
    index_dir = Path(index_dir or index_config.persist_dir)
    collection_name = collection_name or index_config.collection_name
    if not (index_dir / "chroma.sqlite3").is_file():
        raise FileNotFoundError(f"no Chroma index at {index_dir}")

    if embedder is None:
        from backend.ai.embeddings import SentenceTransformerEmbedder

        embedder = SentenceTransformerEmbedder()
    if documents is None:
        from backend.ai.documents import build_all_documents, read_only_session

        with read_only_session() as db:
            documents = build_all_documents(db)

    chunks = chunk_documents(documents, embedder.count_tokens, chunk_config or ChunkingConfig())
    expected = {c.chunk_id: c.metadata["content_hash"] for c in chunks}
    actual = _index_hashes(index_dir, collection_name)

    missing = sorted(expected.keys() - actual.keys())      # in the database, not in the index
    extra = sorted(actual.keys() - expected.keys())        # in the index, not in the database
    changed = sorted(k for k in expected.keys() & actual.keys() if expected[k] != actual[k])
    return {
        "consistent": not (missing or extra or changed),
        "database_documents": len(documents),
        "database_documents_by_type": dict(sorted(Counter(d.doc_type for d in documents).items())),
        "database_chunks": len(expected),
        "index_chunks": len(actual),
        "missing_from_index": {"count": len(missing), "examples": missing[:MAX_LISTED]},
        "not_in_database": {"count": len(extra), "examples": extra[:MAX_LISTED]},
        "content_changed": {"count": len(changed), "examples": changed[:MAX_LISTED]},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--index-dir", type=Path, default=None,
                        help="Chroma directory (default: AI_CHROMA_DIR or ai_index/chroma)")
    parser.add_argument("--json", action="store_true", help="print the full report as JSON")
    args = parser.parse_args(argv)
    try:
        report = check(args.index_dir)
    except Exception as exc:  # noqa: BLE001 - report without leaking connection details
        print(f"Index consistency check could not run: {type(exc).__name__}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"database chunks: {report['database_chunks']}  index chunks: {report['index_chunks']}")
        for key in ("missing_from_index", "not_in_database", "content_changed"):
            print(f"{key}: {report[key]['count']}  {report[key]['examples'][:5]}")
        print("CONSISTENT" if report["consistent"] else "INCONSISTENT: rebuild the index from this database")
    return 0 if report["consistent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
