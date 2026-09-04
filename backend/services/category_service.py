from sqlalchemy.orm import Session

from backend.models.category import Category
from backend.repositories import category_repository
from backend.services.exceptions import ResourceNotFoundError


def list_categories(db: Session) -> list[Category]:
    return category_repository.get_all(db)


def get_category(db: Session, category_id: int) -> Category:
    category = category_repository.get_by_id(db, category_id)

    if category is None:
        raise ResourceNotFoundError("Category", category_id)

    return category
