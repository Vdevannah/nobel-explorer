from backend.database.connection import SessionLocal
from backend.models.category import Category
from backend.repositories.category_repository import (
    create,
    get_all,
    get_by_id,
    get_by_name,
)


def test_category_repository():
    db = SessionLocal()

    try:
        category = Category(
            name="Repository Test Category",
            description="Temporary category for repository testing"
        )

        created_category = create(db, category)

        assert created_category.category_id is not None
        assert created_category.name == "Repository Test Category"

        all_categories = get_all(db)
        print("Total categories found:", len(all_categories))

        found_category = get_by_id(db, category.category_id)

        assert found_category is not None

        print("Category ID:", found_category.category_id)
        print("Category Name:", found_category.name)
        print("Description:", found_category.description)

        found_by_name = get_by_name(db, "Repository Test Category")

        assert found_by_name is not None
        assert found_by_name.category_id == created_category.category_id

        print("Found by Name:", found_by_name.name)

        print("\nCategory repository test passed.")

    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    test_category_repository()
