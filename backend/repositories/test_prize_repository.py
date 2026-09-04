from backend.database.connection import SessionLocal
from backend.models.category import Category
from backend.models.prize import Prize
from backend.repositories.prize_repository import (
    create,
    get_all,
    get_by_id,
    get_by_category,
    get_by_year_and_category,
)


def test_prize_repository():
    db = SessionLocal()

    try:
        category = Category(
            name="Repository Test Chemistry",
            description="Temporary category for prize repository testing"
        )

        db.add(category)
        db.flush()

        prize = Prize(
            year=2024,
            category=category
        )

        created_prize = create(db, prize)

        assert created_prize.prize_id is not None
        assert created_prize.year == 2024

        all_prizes = get_all(db)
        print("Total prizes found:", len(all_prizes))

        found_prize = get_by_id(db, prize.prize_id)

        assert found_prize is not None

        print("Prize ID:", found_prize.prize_id)
        print("Prize Year:", found_prize.year)
        assert not hasattr(found_prize, "motivation")

        category_prizes = get_by_category(
            db,
            category.category_id
        )

        print(
            "Prizes found for category:",
            len(category_prizes)
        )

        print(
            "Category:",
            category_prizes[0].category.name
        )

        found_by_year_and_category = get_by_year_and_category(
            db,
            2024,
            category.category_id
        )

        assert found_by_year_and_category is not None
        assert found_by_year_and_category.prize_id == created_prize.prize_id

        print(
            "Found by Year and Category:",
            found_by_year_and_category.prize_id
        )

        print("\nPrize repository test passed.")

    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    test_prize_repository()
