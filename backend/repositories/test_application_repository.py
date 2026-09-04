from backend.database.connection import SessionLocal

from backend.models.category import Category
from backend.models.prize import Prize
from backend.models.laureate import Laureate
from backend.models.laureate_prize import LaureatePrize
from backend.models.discovery import Discovery
from backend.models.application import Application

from backend.repositories.application_repository import (
    create,
    get_by_id,
    get_by_discovery,
    update,
    delete,
)


def test_application_repository():
    db = SessionLocal()

    try:
        category = Category(
            name="Repository Test Application Category",
            description="Temporary category"
        )

        prize = Prize(
            year=2024,
            category=category
        )

        laureate = Laureate(
            nobel_laureate_id="TEST-015",
            full_name="Test Application Laureate",
            laureate_type="Person",
            featured=True
        )

        laureate_prize = LaureatePrize(
            laureate=laureate,
            prize=prize,
            prize_share="1/1",
            motivation="Temporary Nobel prize"
        )

        discovery = Discovery(
            laureate_prize=laureate_prize,
            title="Test Discovery",
            summary="Temporary discovery",
            significance="Temporary significance"
        )

        db.add(category)
        db.flush()

        # CREATE
        application = Application(
            discovery=discovery,
            title="Original Application",
            description="Original application description",
            source_name="Test Source",
            source_url="https://example.com/original"
        )

        created_application = create(
            db,
            application
        )

        print(
            "Created Application ID:",
            created_application.application_id
        )
        print(
            "Created Title:",
            created_application.title
        )

        # READ BY ID
        found_application = get_by_id(
            db,
            created_application.application_id
        )

        print(
            "Found Application:",
            found_application.title
        )

        # READ BY DISCOVERY
        discovery_applications = get_by_discovery(
            db,
            discovery.discovery_id
        )

        print(
            "Applications found for discovery:",
            len(discovery_applications)
        )

        # UPDATE
        updated_application = update(
            db,
            found_application,
            title="Updated Application",
            description="Updated application description",
            source_name="Updated Source",
            source_url="https://example.com/updated"
        )

        print(
            "Updated Title:",
            updated_application.title
        )
        print(
            "Updated Description:",
            updated_application.description
        )

        # DELETE
        delete(
            db,
            updated_application
        )

        deleted_application = get_by_id(
            db,
            created_application.application_id
        )

        print(
            "Application after delete:",
            deleted_application
        )

        print(
            "\nApplication repository CRUD test passed."
        )

    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    test_application_repository()
