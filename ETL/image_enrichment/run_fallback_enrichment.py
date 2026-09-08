import argparse
import json
import time
from pathlib import Path

from backend.database.connection import SessionLocal
from ETL.image_enrichment.commons import CommonsClient
from ETL.image_enrichment.persistence import apply_persistence, plan_persistence
from ETL.image_enrichment.sources import WikidataClient
from ETL.image_enrichment.wikipedia_fallback import WikipediaClient, enrich_one_fallback


AUDIT_PATH = Path("artifacts/image_enrichment_unresolved_audit.json")
REPORT_PATH = Path("artifacts/image_enrichment_fallback_report.json")
REVIEW_QUEUE_PATH = Path("artifacts/image_enrichment_fallback_review_queue.json")

# Section 2: only these four groups this phase. COMMONS_LICENSE (64) is
# explicitly out of scope pending a separate license-policy review.
ELIGIBLE_CATEGORIES = {"NO_P18", "OTHER", "IDENTITY_AMBIGUOUS", "REVIEW"}

REPORT_FIELDS = (
    "laureate_id", "nobel_laureate_id", "full_name", "original_category",
    "wikipedia_article", "identity_decision", "pageimage_candidate",
    "commons_filename", "commons_decision", "final_action", "reason",
    "database_write",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 7.5H: Wikipedia PageImage / article-image fallback for "
            "laureates unresolved by the primary Wikidata P18 pipeline. "
            "Defaults to a safe dry-run."
        )
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--dry-run", action="store_true", help="Preview without writing (default).")
    mode_group.add_argument("--persist", action="store_true", help="Persist ACCEPT records to the database.")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument(
        "--exclude-nobel-ids", default="",
        help=(
            "Comma-separated nobel_laureate_ids to exclude entirely (e.g. "
            "quality-gate rejects found during dry-run review, such as a "
            "PageImage that turned out to be a diagram rather than a "
            "portrait). Never processed, never persisted."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    mode = "persist" if args.persist else "dry-run"

    excluded_ids = {value.strip() for value in args.exclude_nobel_ids.split(",") if value.strip()}

    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    eligible = [
        r for r in audit["records"]
        if r["category"] in ELIGIBLE_CATEGORIES and r["nobel_laureate_id"] not in excluded_ids
    ]
    print(f"eligible records this phase: {len(eligible)} (of {audit['total_unresolved']} total unresolved)")
    print(f"skipping {audit['total_unresolved'] - len(eligible) - len(excluded_ids)} COMMONS_LICENSE records (separate license review)")
    if excluded_ids:
        print(f"quality-gate excluded: {sorted(excluded_ids)}")

    db = SessionLocal()
    wikidata_client = WikidataClient()
    wikipedia_client = WikipediaClient()
    commons_client = CommonsClient()

    results = []
    start_time = time.monotonic()
    try:
        for index, record in enumerate(eligible):
            step_start = time.monotonic()
            result = enrich_one_fallback(
                db,
                record["nobel_laureate_id"],
                record["category"],
                wikidata_client,
                wikipedia_client,
                commons_client,
                candidate_wikidata_id=record.get("candidate_wikidata_id"),
                existing_p18_filename=record.get("p18_filename"),
            )
            results.append(result)
            elapsed = time.monotonic() - step_start
            total = time.monotonic() - start_time
            print(
                f"  [{total:6.1f}s total, {elapsed:5.1f}s this record] "
                f"({index + 1}/{len(eligible)}) {record['nobel_laureate_id']} "
                f"{result['full_name']!r} | category={record['category']} "
                f"identity={result['identity_decision']} "
                f"article={result['wikipedia_article']!r} "
                f"commons={result['commons_decision']} "
                f"action={result['final_action']}",
                flush=True,
            )

        counts = {
            "total_considered": len(eligible),
            "identity_accept": sum(1 for r in results if r["identity_decision"] == "ACCEPT"),
            "identity_review": sum(1 for r in results if r["identity_decision"] == "REVIEW"),
            "identity_skip": sum(1 for r in results if r["identity_decision"] == "SKIP"),
            "pageimage_found": sum(
                1 for r in results if r["commons_filename"] and r["final_action"] != "skipped_existing"
                and r.get("pageimage_candidate") and r["wikipedia_article"]
            ),
            "commons_accept": sum(1 for r in results if r["commons_decision"] == "ACCEPT"),
            "commons_review": sum(1 for r in results if r["commons_decision"] == "REVIEW"),
            "commons_skip": sum(1 for r in results if r["commons_decision"] == "SKIP"),
            "final_accept": sum(1 for r in results if r["final_action"] == "accept"),
            "final_review": sum(1 for r in results if r["final_action"] == "review"),
            "final_skip": sum(1 for r in results if r["final_action"] == "skip"),
            "skipped_existing": sum(1 for r in results if r["final_action"] == "skipped_existing"),
        }

        by_category = {}
        for category in ("NO_P18", "OTHER", "IDENTITY_AMBIGUOUS", "REVIEW"):
            subset = [r for r in results if r["original_category"] == category]
            by_category[category] = {
                "considered": len(subset),
                "final_accept": sum(1 for r in subset if r["final_action"] == "accept"),
            }
        counts["by_category"] = by_category

        persisted_ids: list[str] = []
        if mode == "persist":
            acceptable = [r["_commons_result"] for r in results if r["final_action"] == "accept"]
            plans = plan_persistence(db, acceptable, force=False)
            apply_result = apply_persistence(db, plans)
            if not apply_result["committed"]:
                raise RuntimeError(f"persistence failed: {apply_result['error']}")
            persisted_ids = apply_result["updated_ids"]
            for result in results:
                if result["nobel_laureate_id"] in persisted_ids:
                    result["database_write"] = True
            counts["persisted"] = len(persisted_ids)
    finally:
        if mode == "dry-run":
            db.rollback()
        db.close()

    review_queue = [
        {field: r.get(field) for field in REPORT_FIELDS}
        for r in results
        if r["final_action"] in ("review", "skip")
    ]

    report_output = {
        "mode": mode,
        "counts": counts,
        "records": [{field: r.get(field) for field in REPORT_FIELDS} for r in results],
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report_output, indent=2, ensure_ascii=False), encoding="utf-8")
    REVIEW_QUEUE_PATH.write_text(json.dumps(review_queue, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=== SUMMARY ===")
    for key, value in counts.items():
        if key != "by_category":
            print(f"{key}: {value}")
    print("by_category:", json.dumps(counts["by_category"], indent=2))
    print(f"Report written to {REPORT_PATH}")
    print(f"Review queue written to {REVIEW_QUEUE_PATH} ({len(review_queue)} records)")


if __name__ == "__main__":
    main()
