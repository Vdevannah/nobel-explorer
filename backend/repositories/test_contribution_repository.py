from backend.database.connection import SessionLocal
from backend.models.category import Category
from backend.models.contribution import Contribution
from backend.models.laureate import Laureate
from backend.models.laureate_prize import LaureatePrize
from backend.models.prize import Prize
from backend.repositories.contribution_repository import (
    create,
    delete,
    get_by_id,
    get_by_laureate,
    get_by_laureate_prize,
    update,
)


def test_contribution_repository():
    db = SessionLocal()
    try:
        category = Category(name="Repository Test Contribution Category")
        prize = Prize(year=2024, category=category)
        laureate = Laureate(
            nobel_laureate_id="TEST-018",
            full_name="Test Contribution Laureate",
            laureate_type="Person",
            featured=True,
        )
        laureate_prize = LaureatePrize(
            laureate=laureate,
            prize=prize,
            prize_share="1/1",
        )
        db.add(category)
        db.flush()

        nobel_contribution = create(
            db,
            Contribution(
                laureate=laureate,
                laureate_prize=laureate_prize,
                contribution_type="NOBEL_LINKED",
                title="Original Contribution",
                summary="Original summary",
                significance="Original significance",
                source_url="https://example.com/original",
            ),
        )
        beyond_nobel = create(
            db,
            Contribution(
                laureate=laureate,
                contribution_type="BEYOND_NOBEL",
                title="Beyond Nobel Contribution",
            ),
        )

        assert get_by_id(db, nobel_contribution.contribution_id) is nobel_contribution
        laureate_contributions = get_by_laureate(db, laureate.laureate_id)
        assert {
            contribution.contribution_id
            for contribution in laureate_contributions
        } == {
            nobel_contribution.contribution_id,
            beyond_nobel.contribution_id,
        }
        assert get_by_laureate_prize(db, laureate_prize.laureate_prize_id) == [
            nobel_contribution
        ]
        assert beyond_nobel.laureate_prize_id is None

        updated = update(
            db,
            nobel_contribution,
            laureate_id=laureate.laureate_id,
            laureate_prize_id=laureate_prize.laureate_prize_id,
            contribution_type="NOBEL_LINKED",
            title="Updated Contribution",
            summary="Updated summary",
            significance="Updated significance",
            source_url="https://example.com/updated",
        )
        assert updated.title == "Updated Contribution"

        contribution_id = beyond_nobel.contribution_id
        delete(db, beyond_nobel)
        assert get_by_id(db, contribution_id) is None
    finally:
        db.rollback()
        db.close()
