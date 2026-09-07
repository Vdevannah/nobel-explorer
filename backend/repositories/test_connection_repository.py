from backend.database.connection import SessionLocal
from backend.models.category import Category
from backend.models.connection import Connection
from backend.models.contribution import Contribution
from backend.models.laureate import Laureate
from backend.models.laureate_prize import LaureatePrize
from backend.models.prize import Prize
from backend.repositories.connection_repository import (
    create,
    delete,
    get_by_contribution,
    get_by_id,
    update,
)


def test_connection_repository():
    db = SessionLocal()
    try:
        category = Category(name="Repository Test Connection Category")
        prize = Prize(year=2024, category=category)
        related_prize = Prize(year=2023, category=category)
        laureate = Laureate(
            nobel_laureate_id="TEST-015",
            full_name="Test Connection Laureate",
            laureate_type="Person",
            featured=True,
        )
        laureate_prize = LaureatePrize(laureate=laureate, prize=prize)
        contribution = Contribution(
            laureate=laureate,
            laureate_prize=laureate_prize,
            contribution_type="NOBEL_LINKED",
            title="Test Contribution",
        )
        db.add_all([category, related_prize, contribution])
        db.flush()

        application = create(
            db,
            Connection(
                contribution=contribution,
                connection_type="APPLICATION",
                title="Original Connection",
                description="Original description",
            ),
        )
        legacy = create(
            db,
            Connection(
                contribution=contribution,
                connection_type="SCIENTIFIC_LEGACY",
                related_prize=related_prize,
                title="Later Nobel-recognized legacy",
            ),
        )

        assert get_by_id(db, application.connection_id) is application
        assert get_by_contribution(db, contribution.contribution_id) == [
            application,
            legacy,
        ]
        assert legacy.related_prize_id == related_prize.prize_id

        updated = update(
            db,
            application,
            connection_type="EXPERIMENTAL_VALIDATION",
            title="Updated Connection",
            description="Updated description",
            source_name="Updated Source",
            source_url="https://example.com/updated",
            related_prize_id=None,
        )
        assert updated.connection_type == "EXPERIMENTAL_VALIDATION"

        connection_id = updated.connection_id
        delete(db, updated)
        assert get_by_id(db, connection_id) is None
    finally:
        db.rollback()
        db.close()
