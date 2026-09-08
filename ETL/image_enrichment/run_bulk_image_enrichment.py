import argparse
import json
import time
from pathlib import Path

from backend.database.connection import SessionLocal
from ETL.image_enrichment.bulk import run_bulk_enrichment, select_missing_image_nobel_ids


BULK_REPORT_PATH = Path("artifacts/image_enrichment_bulk_report.json")
REVIEW_QUEUE_PATH = Path("artifacts/image_enrichment_review_queue.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bulk Wikidata identity + Commons license validation + "
            "safe persistence, reusing the Phase 7.5C/D/E pipeline "
            "unchanged. Defaults to a safe, missing-only dry-run."
        )
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run", action="store_true",
        help="Preview without writing (default).",
    )
    mode_group.add_argument(
        "--persist", action="store_true",
        help="Persist ACCEPT+ACCEPT records to the database.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max laureates to consider.")
    parser.add_argument("--offset", type=int, default=0, help="Skip the first N candidates.")
    parser.add_argument(
        "--batch-size", type=int, default=50,
        help="Internal chunk size for pacing/commits (default 50).",
    )
    parser.add_argument(
        "--missing-only", action="store_true", default=True,
        help="Only consider laureates without image_url (default; on unless --force).",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Also reprocess laureates that already have image_url.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    mode = "persist" if args.persist else "dry-run"

    db = SessionLocal()
    try:
        nobel_ids = select_missing_image_nobel_ids(
            db, limit=args.limit, offset=args.offset, force=args.force
        )
        print(
            f"selected {len(nobel_ids)} laureate(s) "
            f"(offset={args.offset}, limit={args.limit}, force={args.force})",
            flush=True,
        )

        start_time = time.monotonic()
        last_record_time = [start_time]

        def on_record(chunk_index, nobel_id, result):
            now = time.monotonic()
            step_seconds = now - last_record_time[0]
            last_record_time[0] = now
            print(
                f"  [{now - start_time:6.1f}s total, {step_seconds:5.1f}s this record] "
                f"chunk {chunk_index} | {nobel_id} {result.get('full_name')!r} | "
                f"identity={result.get('identity_decision')} "
                f"p18={'yes' if result.get('p18_filename') else 'no'} "
                f"commons={result.get('commons_decision')}",
                flush=True,
            )

        def progress(chunk_index, counts, stop_reason):
            print(
                f"chunk {chunk_index} done: processed={counts['total_processed']} "
                f"identity_accept={counts['identity_accept']} "
                f"commons_accept={counts['commons_accept']} "
                f"persisted={counts['persisted']}"
                + (f" | STOP: {stop_reason}" if stop_reason else ""),
                flush=True,
            )

        report = run_bulk_enrichment(
            db,
            nobel_ids,
            mode=mode,
            force=args.force,
            batch_size=args.batch_size,
            progress_callback=progress,
            record_callback=on_record,
        )
    finally:
        if mode == "dry-run":
            db.rollback()
        db.close()

    BULK_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    bulk_output = {key: value for key, value in report.items() if key != "review_queue"}
    BULK_REPORT_PATH.write_text(
        json.dumps(bulk_output, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    REVIEW_QUEUE_PATH.write_text(
        json.dumps(report["review_queue"], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("=== SUMMARY ===")
    for key, value in report["counts"].items():
        print(f"{key}: {value}")
    if report["stopped_early"]:
        print(f"STOPPED EARLY: {report['stop_reason']}")
    print(f"Bulk report written to {BULK_REPORT_PATH}")
    print(f"Review queue written to {REVIEW_QUEUE_PATH} ({len(report['review_queue'])} records)")


if __name__ == "__main__":
    main()
