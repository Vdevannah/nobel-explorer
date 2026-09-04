from backend.database.connection import SessionLocal
from backend.models.laureate import Laureate
from backend.repositories.laureate_repository import (
    create,
    get_all,
    get_by_id,
    get_by_nobel_id,
    get_featured,
)


def test_laureate_repository():
    db = SessionLocal()

    try:
        featured_laureate = Laureate(
            nobel_laureate_id="TEST-016",
            full_name="Test Featured Laureate",
            laureate_type="Person",
            birth_city="Test City",
            birth_state="Delaware",
            birth_country="USA",
            gender="Female",
            featured=True
        )

        regular_laureate = Laureate(
            nobel_laureate_id="TEST-017",
            full_name="Test Regular Laureate",
            laureate_type="Person",
            birth_city="Another City",
            birth_state="Pennsylvania",
            birth_country="USA",
            gender="Male",
            featured=False
        )

        nobel_id_laureate = Laureate(
            nobel_laureate_id="TEST-NOBEL-ID-001",
            full_name="Test Nobel ID Laureate",
            laureate_type="Person",
            featured=False
        )

        created_featured = create(db, featured_laureate)
        created_regular = create(db, regular_laureate)
        create(db, nobel_id_laureate)

        assert created_featured.laureate_id is not None
        assert created_regular.laureate_id is not None

        all_laureates = get_all(db)

        print(
            "Total laureates found:",
            len(all_laureates)
        )

        found_laureate = get_by_id(
            db,
            featured_laureate.laureate_id
        )

        assert found_laureate is not None

        found_by_nobel_id = get_by_nobel_id(
            db,
            "TEST-NOBEL-ID-001"
        )

        assert found_by_nobel_id is not None
        assert found_by_nobel_id.nobel_laureate_id == "TEST-NOBEL-ID-001"
        assert found_by_nobel_id.full_name == nobel_id_laureate.full_name

        missing_by_nobel_id = get_by_nobel_id(
            db,
            "DOES-NOT-EXIST"
        )

        assert missing_by_nobel_id is None

        print(
            "Laureate ID:",
            found_laureate.laureate_id
        )
        print(
            "Laureate Name:",
            found_laureate.full_name
        )
        print(
            "Laureate Type:",
            found_laureate.laureate_type
        )
        print(
            "Birth State:",
            found_laureate.birth_state
        )

        featured_laureates = get_featured(db)

        print(
            "Featured laureates found:",
            len(featured_laureates)
        )

        print(
            "Featured Laureate:",
            featured_laureates[0].full_name
        )

        print("\nLaureate repository test passed.")

    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    test_laureate_repository()
