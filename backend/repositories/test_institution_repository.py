from backend.database.connection import SessionLocal
from backend.models.institution import Institution

from backend.repositories.institution_repository import (
    create,
    get_all,
    get_by_id,
    get_by_name,
)


def test_institution_repository():
    db = SessionLocal()

    try:
        institution = Institution(
            name="Repository Test University",
            city="Test City",
            state="Delaware",
            country="USA"
        )

        created_institution = create(db, institution)

        assert created_institution.institution_id is not None
        assert created_institution.name == "Repository Test University"

        all_institutions = get_all(db)

        print(
            "Total institutions found:",
            len(all_institutions)
        )

        found_by_id = get_by_id(
            db,
            institution.institution_id
        )

        assert found_by_id is not None

        print(
            "Institution ID:",
            found_by_id.institution_id
        )

        print(
            "Institution Name:",
            found_by_id.name
        )

        found_by_name = get_by_name(
            db,
            "Repository Test University"
        )

        assert found_by_name is not None

        print(
            "Found by Name:",
            found_by_name.name
        )

        print(
            "Institution State:",
            found_by_name.state
        )

        print("\nInstitution repository test passed.")

    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    test_institution_repository()
