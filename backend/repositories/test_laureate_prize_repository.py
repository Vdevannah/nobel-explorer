from backend.database.connection import SessionLocal
from backend.models.category import Category
from backend.models.prize import Prize
from backend.models.laureate import Laureate
from backend.models.laureate_prize import LaureatePrize

from backend.repositories.laureate_prize_repository import (
    create,
    get_by_id,
    get_by_laureate,
    get_by_prize,
)


def test_laureate_prize_repository():
    db = SessionLocal()

    try:
        category = Category(
            name="Repository Test Physics",
            description="Temporary category"
        )

        prize = Prize(
            year=2024,
            motivation="Temporary Nobel prize",
            category=category
        )

        laureate_one = Laureate(
            full_name="Test Laureate One",
            laureate_type="Person",
            featured=False
        )

        laureate_two = Laureate(
            full_name="Test Laureate Two",
            laureate_type="Person",
            featured=False
        )

        db.add_all([category, laureate_one, laureate_two])
        db.flush()

        award_one = LaureatePrize(
            laureate=laureate_one,
            prize=prize,
            prize_share="1/2"
        )

        created_award_one = create(db, award_one)

        award_two = LaureatePrize(
            laureate=laureate_two,
            prize=prize,
            prize_share="1/2"
        )

        created_award_two = create(db, award_two)

        assert created_award_one.laureate_prize_id is not None
        assert created_award_two.laureate_prize_id is not None

        found_award = get_by_id(
            db,
            award_one.laureate_prize_id
        )

        assert found_award is not None

        print("Award ID:", found_award.laureate_prize_id)
        print("Laureate:", found_award.laureate.full_name)
        print("Prize Year:", found_award.prize.year)
        print("Prize Share:", found_award.prize_share)

        laureate_awards = get_by_laureate(
            db,
            laureate_one.laureate_id
        )

        print(
            "Awards found for laureate:",
            len(laureate_awards)
        )

        prize_awards = get_by_prize(
            db,
            prize.prize_id
        )

        print(
            "Laureates found for prize:",
            len(prize_awards)
        )

        for award in prize_awards:
            print(
                "Prize Laureate:",
                award.laureate.full_name
            )

        print("\nLaureatePrize repository test passed.")

    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    test_laureate_prize_repository()
