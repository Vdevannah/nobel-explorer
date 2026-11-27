"""Read-only index/database consistency check (fixture database, hashing embedder)."""

import dataclasses
import hashlib

import pytest

pytest.importorskip("chromadb")

from backend.ai import build_index  # noqa: E402
from backend.ai.check_index_consistency import check  # noqa: E402


def _tree_digest(path):
    return {p.relative_to(path).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob("*")) if p.is_file()}


@pytest.fixture()
def built(documents, hashing_embedder, index_config, tmp_path):
    build_index.run(embedder=hashing_embedder, index_config=index_config, documents=documents,
                    manifest_path=tmp_path / "manifest.json")
    return index_config


def test_identical_database_is_consistent_and_index_is_untouched(built, documents, hashing_embedder):
    before = _tree_digest(built.persist_dir)
    report = check(built.persist_dir, documents=documents, embedder=hashing_embedder,
                   collection_name=built.collection_name)
    assert report["consistent"] and report["database_chunks"] == report["index_chunks"] > 0
    assert _tree_digest(built.persist_dir) == before  # opened from a temporary copy only


def test_changed_internal_ids_are_detected(built, documents, hashing_embedder):
    doc = next(d for d in documents if "laureate_ids" in d.metadata)
    shifted = dataclasses.replace(doc, metadata={**doc.metadata, "laureate_ids": [i + 1000 for i in
                                                                                    doc.metadata["laureate_ids"]]})
    altered = [shifted if d is doc else d for d in documents]
    report = check(built.persist_dir, documents=altered, embedder=hashing_embedder,
                   collection_name=built.collection_name)
    assert not report["consistent"] and report["content_changed"]["count"] >= 1


def test_missing_and_extra_records_are_detected(built, documents, hashing_embedder):
    extra = dataclasses.replace(documents[0], doc_id="laureate:nobel-999999")
    report = check(built.persist_dir, documents=documents[1:] + [extra], embedder=hashing_embedder,
                   collection_name=built.collection_name)
    assert report["missing_from_index"]["count"] >= 1 and report["not_in_database"]["count"] >= 1


def test_report_contains_ids_and_counts_only(built, documents, hashing_embedder):
    report = check(built.persist_dir, documents=documents, embedder=hashing_embedder,
                   collection_name=built.collection_name)
    text = repr(report)
    assert all(doc.text[:40] not in text for doc in documents)
