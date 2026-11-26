"""Evaluate retrieval quality against ``retrieval_eval_set.json``.

    python -m backend.ai.evaluation.run_retrieval_eval [--output PATH]

Relevance level
---------------
* Ranking is at CHUNK level: the search returns up to 10 chunks, in order.
* Relevance is judged at PARENT-DOCUMENT level: each chunk is mapped to its
  ``doc_id`` (e.g. ``explanation:609:expert#c3`` -> ``explanation:609:expert``)
  and compared with the ground-truth ``relevant`` doc ids.
* It is NOT contribution level: ``contribution:38`` and
  ``explanation:38:simple`` are different documents, and a question only
  credits the ids listed for it.
* Consequence: two chunks of the same document occupy two rank positions but
  count once for recall, so duplicate chunks can lower Recall@5.

Metrics (per question, then averaged over in-scope questions)
-------------------------------------------------------------
* Hit@3    = 1 if any of the top-3 chunks maps to a relevant doc, else 0.
* Recall@5 = |relevant docs among the top-5 chunks' doc ids| / |relevant docs|.
* MRR@10   = mean of 1 / (rank of the first relevant chunk), 0 if none in top-10.
* Latency  = wall-clock time of ``search_nobel_knowledge`` (query embedding +
             Chroma query) for every query (in-scope and out-of-scope), after
             one warm-up call. Percentiles use the nearest-rank method.

Out-of-scope questions are reported separately: nearest-neighbour search
always returns something, so their top-1 similarity is compared with
in-scope top-1 similarity to judge whether a score threshold could help.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from backend.ai.retrieval import search_nobel_knowledge

DATASET = Path(__file__).with_name("retrieval_eval_set.json")
RETRIEVE_K = 10


def _ranked_doc_ids(response) -> list[str]:
    return [r.doc_id for r in response.results]


def hit_at_k(ranked_doc_ids: list[str], relevant: set[str], k: int) -> bool:
    return any(doc_id in relevant for doc_id in ranked_doc_ids[:k])


def recall_at_k(ranked_doc_ids: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        raise ValueError("relevant set must not be empty")
    return len(relevant & set(ranked_doc_ids[:k])) / len(relevant)


def first_relevant_rank(ranked_doc_ids: list[str], relevant: set[str], k: int) -> int | None:
    return next((i + 1 for i, doc_id in enumerate(ranked_doc_ids[:k]) if doc_id in relevant), None)


def reciprocal_rank(ranked_doc_ids: list[str], relevant: set[str], k: int) -> float:
    rank = first_relevant_rank(ranked_doc_ids, relevant, k)
    return 1.0 / rank if rank else 0.0


def _percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(pct / 100 * (len(ordered) - 1))))
    return ordered[index]


def evaluate(store=None, dataset_path: Path = DATASET, dedupe_by_document: bool = False) -> dict:
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if store is None:
        from backend.ai.retrieval import get_default_store
        store = get_default_store()

    # Guard against typos in ground truth: every expected id must exist.
    stored_ids = {cid.split("#", 1)[0] for cid in store.collection.get(include=[])["ids"]}
    missing = sorted({d for q in dataset["in_scope"] for d in q["relevant"]} - stored_ids)
    if missing:
        raise ValueError(f"Ground-truth doc ids not present in the index: {missing}")

    search_nobel_knowledge("warm up", k=1, store=store)

    per_question = []
    latencies = []
    for item in dataset["in_scope"]:
        started = time.perf_counter()
        response = search_nobel_knowledge(item["query"], level=item.get("level"), k=RETRIEVE_K, store=store,
                                          dedupe_by_document=dedupe_by_document)
        latency_ms = (time.perf_counter() - started) * 1000
        latencies.append(latency_ms)

        ranked = _ranked_doc_ids(response)
        relevant = set(item["relevant"])
        per_question.append({
            "id": item["id"],
            "topic": item["topic"],
            "kind": item["kind"],
            "query": item["query"],
            "level": item.get("level"),
            "hit_at_3": hit_at_k(ranked, relevant, 3),
            "recall_at_5": round(recall_at_k(ranked, relevant, 5), 4),
            "reciprocal_rank": round(reciprocal_rank(ranked, relevant, RETRIEVE_K), 4),
            "first_relevant_rank": first_relevant_rank(ranked, relevant, RETRIEVE_K),
            "top1_similarity": response.results[0].similarity if response.results else None,
            "top5": [
                {"doc_id": r.doc_id, "similarity": round(r.similarity, 4), "relevant": r.doc_id in relevant}
                for r in response.results[:5]
            ],
            "latency_ms": round(latency_ms, 2),
        })

    oos = []
    for item in dataset["out_of_scope"]:
        started = time.perf_counter()
        response = search_nobel_knowledge(item["query"], k=3, store=store, dedupe_by_document=dedupe_by_document)
        latencies.append((time.perf_counter() - started) * 1000)
        oos.append({
            "id": item["id"],
            "query": item["query"],
            "top1_similarity": response.results[0].similarity if response.results else None,
            "top3": [{"doc_id": r.doc_id, "similarity": round(r.similarity, 4)} for r in response.results],
        })

    n = len(per_question)
    in_top1 = [q["top1_similarity"] for q in per_question if q["top1_similarity"] is not None]
    oos_top1 = [q["top1_similarity"] for q in oos if q["top1_similarity"] is not None]
    thresholds = []
    for t in (0.25, 0.30, 0.35, 0.40, 0.45, 0.50):
        thresholds.append({
            "min_similarity": t,
            "in_scope_top1_kept": sum(s >= t for s in in_top1),
            "out_of_scope_top1_rejected": sum(s < t for s in oos_top1),
        })

    return {
        "dataset_version": dataset["version"],
        "dedupe_by_document": dedupe_by_document,
        "retrieve_k": RETRIEVE_K,
        "in_scope_questions": n,
        "out_of_scope_questions": len(oos),
        "metrics": {
            "hit_at_3": round(sum(q["hit_at_3"] for q in per_question) / n, 4),
            "recall_at_5": round(sum(q["recall_at_5"] for q in per_question) / n, 4),
            "mrr_at_10": round(sum(q["reciprocal_rank"] for q in per_question) / n, 4),
        },
        "metrics_by_topic": {
            topic: {
                "n": len(rows),
                "hit_at_3": round(sum(r["hit_at_3"] for r in rows) / len(rows), 4),
                "recall_at_5": round(sum(r["recall_at_5"] for r in rows) / len(rows), 4),
                "mrr_at_10": round(sum(r["reciprocal_rank"] for r in rows) / len(rows), 4),
            }
            for topic in sorted({q["topic"] for q in per_question})
            for rows in [[q for q in per_question if q["topic"] == topic]]
        },
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 2),
            "p50": round(_percentile(latencies, 50), 2),
            "p95": round(_percentile(latencies, 95), 2),
            "max": round(max(latencies), 2),
        },
        "similarity_separation": {
            "in_scope_top1_min": round(min(in_top1), 4),
            "in_scope_top1_median": round(statistics.median(in_top1), 4),
            "out_of_scope_top1_max": round(max(oos_top1), 4),
            "out_of_scope_top1_median": round(statistics.median(oos_top1), 4),
            "threshold_analysis": thresholds,
        },
        "failures": [q for q in per_question if not q["hit_at_3"] or q["recall_at_5"] < 1.0],
        "per_question": per_question,
        "out_of_scope": oos,
    }


def compare_dedupe(store=None, dataset_path: Path = DATASET) -> dict:
    """Run the same questions with and without document de-duplication."""
    if store is None:
        from backend.ai.retrieval import get_default_store
        store = get_default_store()
    baseline = evaluate(store, dataset_path, dedupe_by_document=False)
    deduped = evaluate(store, dataset_path, dedupe_by_document=True)
    per_question = []
    for b, d in zip(baseline["per_question"], deduped["per_question"]):
        per_question.append({
            "id": b["id"],
            "query": b["query"],
            "hit_at_3": [b["hit_at_3"], d["hit_at_3"]],
            "recall_at_5": [b["recall_at_5"], d["recall_at_5"]],
            "reciprocal_rank": [b["reciprocal_rank"], d["reciprocal_rank"]],
            "changed": (b["hit_at_3"], b["recall_at_5"], b["reciprocal_rank"])
                       != (d["hit_at_3"], d["recall_at_5"], d["reciprocal_rank"]),
        })
    return {
        "baseline": {k: baseline[k] for k in ("metrics", "metrics_by_topic", "latency_ms")},
        "deduplicated": {k: deduped[k] for k in ("metrics", "metrics_by_topic", "latency_ms")},
        "questions_changed": sum(q["changed"] for q in per_question),
        "per_question": per_question,
        "baseline_full": baseline,
        "deduplicated_full": deduped,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the retrieval evaluation")
    parser.add_argument("--output", type=Path, default=None, help="write full JSON results here")
    parser.add_argument("--dedupe", action="store_true", help="evaluate with document de-duplication")
    parser.add_argument("--compare-dedupe", action="store_true", help="compare baseline vs de-duplicated")
    args = parser.parse_args(argv)
    if args.compare_dedupe:
        results = compare_dedupe()
        summary = {k: results[k] for k in ("baseline", "deduplicated", "questions_changed")}
    else:
        results = evaluate(dedupe_by_document=args.dedupe)
        summary = {k: results[k] for k in ("metrics", "metrics_by_topic", "latency_ms", "similarity_separation")}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
