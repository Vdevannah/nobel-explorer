from backend.database.connection import SessionLocal
from ETL.extract import fetch_all_laureates
from ETL.load import load_laureate_record
from ETL.transform import transform_laureate, transform_prizes


def run_etl(max_laureates: int | None = None) -> None:
    raw_laureates = fetch_all_laureates()

    if max_laureates is not None:
        raw_laureates = raw_laureates[:max_laureates]

    db = SessionLocal()
    loaded_count = 0
    skipped_count = 0
    total_count = len(raw_laureates)

    try:
        for index, raw_laureate in enumerate(raw_laureates, start=1):
            laureate_data = transform_laureate(raw_laureate)
            prize_data = transform_prizes(raw_laureate)

            if not prize_data:
                skipped_count += 1
                print(
                    f"Skipping laureate {index}/{total_count}: "
                    f"{laureate_data['full_name']}"
                )
                continue

            print(
                f"Processing laureate {index}/{total_count}: "
                f"{laureate_data['full_name']}"
            )

            load_laureate_record(
                db,
                laureate_data,
                raw_laureate.get("nobelPrizes", [])
            )
            loaded_count += 1

        db.commit()

        print(
            f"ETL complete: {total_count} raw laureates considered, "
            f"{loaded_count} laureates loaded/reused, "
            f"{skipped_count} skipped."
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_etl()
