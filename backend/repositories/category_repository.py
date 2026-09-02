from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.category import Category


def get_all(db: Session) -> list[Category]:
    statement = select(Category)
    return list(db.scalars(statement).all())


def get_by_id(db: Session, category_id: int) -> Category | None:
    statement = select(Category).where(
        Category.category_id == category_id
    )
    return db.scalar(statement)


def create(db: Session, category: Category) -> Category:
    db.add(category)
    db.flush()
    db.refresh(category)
    return category

def get_by_name(db: Session, name: str) -> Category | None:
    statement = select(Category).where(
        Category.name == name
    )
    return db.scalar(statement)