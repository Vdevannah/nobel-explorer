from backend.database.connection import SessionLocal

from backend.models.category import Category
from backend.models.prize import Prize
from backend.models.laureate import Laureate
from backend.models.laureate_prize import LaureatePrize
from backend.models.discovery import Discovery

from backend.repositories.discovery_repository import (
    create,
    get_by_id,
    get_by_laureate_prize,
    update,
    delete,
)


def test_discovery_repository():
    db = SessionLocal()

    try:
        category = Category(
            name="Repository Test Chemistry",
            description="Temporary category"
        )

        prize = Prize(
            year=2024,
            motivation="Temporary Nobel prize",
            category=category
        )

        laureate = Laureate(
            full_name="Test Discovery Laureate",
            laureate_type="Person",
            featured=True
        )

        laureate_prize = LaureatePrize(
            laureate=laureate,
            prize=prize,
            prize_share="1/1"
        )

        db.add(category)
        db.flush()

        # CREATE
        discovery = Discovery(
            laureate_prize=laureate_prize,
            title="Original Discovery Title",
            summary="Original summary",
            significance="Original significance",
            source_url="https://example.com/original"
        )

        created_discovery = create(
            db,
            discovery
        )

        print("Created Discovery ID:", created_discovery.discovery_id)
        print("Created Title:", created_discovery.title)

        # READ BY ID
        found_discovery = get_by_id(
            db,
            created_discovery.discovery_id
        )

        print("Found Discovery:", found_discovery.title)

        # READ BY LAUREATE PRIZE
        award_discoveries = get_by_laureate_prize(
            db,
            laureate_prize.laureate_prize_id
        )

        print(
            "Discoveries found for award:",
            len(award_discoveries)
        )

        # UPDATE
        updated_discovery = update(
            db,
            found_discovery,
            title="Updated Discovery Title",
            summary="Updated summary",
            significance="Updated significance",
            source_url="https://example.com/updated"
        )

        print("Updated Title:", updated_discovery.title)
        print("Updated Summary:", updated_discovery.summary)

        # DELETE
        delete(
            db,
            updated_discovery
        )

        deleted_discovery = get_by_id(
            db,
            created_discovery.discovery_id
        )

        print("Discovery after delete:", deleted_discovery)

        print("\nDiscovery repository CRUD test passed.")

    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    test_discovery_repository()