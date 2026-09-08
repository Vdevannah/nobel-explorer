import argparse
import json
from pathlib import Path

from backend.database.connection import SessionLocal
from ETL.image_enrichment.persistence import load_commons_report, run_persistence


COMMONS_REPORT_PATH = Path("artifacts/image_enrichment_commons_dry_run.json")
DRY_RUN_REPORT_PATH = Path("artifacts/image_enrichment_persistence_dry_run.json")
PERSIST_REPORT_PATH = Path("artifacts/image_enrichment_persistence_result.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Persist Phase 7.5D-approved Commons image metadata onto "
            "existing Laureate rows. Defaults to a safe dry-run."
        )
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be written without writing (default).",
    )
    mode_group.add_argument(
        "--persist",
        action="store_true",
        help="Actually write approved image metadata to the database.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Overwrite existing image metadata too. Default is "
            "missing-only: rows with image_url already set are skipped."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    mode = "persist" if args.persist else "dry-run"

    commons_results = load_commons_report(COMMONS_REPORT_PATH)

    db = SessionLocal()
    try:
        report = run_persistence(db, commons_results, mode=mode, force=args.force)
    finally:
        if mode == "dry-run":
            db.rollback()
        db.close()

    output_path = DRY_RUN_REPORT_PATH if mode == "dry-run" else PERSIST_REPORT_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"mode={mode} force={args.force}")
    print(
        f"updated={report['updated']} "
        f"skipped_existing={report['skipped_existing']} "
        f"review={report['review']} "
        f"skip={report['skip']} "
        f"failed={report['failed']}"
    )
    for record in report["records"]:
        print(
            record.get("nobel_laureate_id"),
            record.get("full_name"),
            record["action"],
        )
    print(f"Report written to {output_path}")


if __name__ == "__main__":
    main()
