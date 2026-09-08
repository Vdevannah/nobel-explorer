import json
from pathlib import Path

from backend.database.connection import SessionLocal
from ETL.image_enrichment.enrichment import run_dry_run


PROTOTYPE_NOBEL_IDS = [
    "26",
    "6",
    "217",
    "743",
    "745",
    "914",
    "1004",
    "1043",
]
REPORT_PATH = Path("artifacts/image_enrichment_wikidata_dry_run.json")


def main() -> None:
    db = SessionLocal()
    try:
        report = run_dry_run(db, PROTOTYPE_NOBEL_IDS)
    finally:
        db.rollback()
        db.close()

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    for result in report["results"]:
        print(
            result.get("nobel_laureate_id"),
            result.get("full_name", "unknown"),
            result.get("selected_entity_id"),
            result.get("confidence"),
            result.get("proposed_action"),
        )
    print(f"Dry-run report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
