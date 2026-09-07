from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.explanation import Explanation


def get_by_id(
    db: Session,
    explanation_id: int
) -> Explanation | None:
    statement = select(Explanation).where(
        Explanation.explanation_id == explanation_id
    )
    return db.scalar(statement)


def get_by_contribution(
    db: Session,
    contribution_id: int,
    level: str | None = None,
) -> list[Explanation]:
    statement = select(Explanation).where(
        Explanation.contribution_id == contribution_id
    )
    if level is not None:
        statement = statement.where(Explanation.level == level)
    statement = statement.order_by(Explanation.explanation_id)
    return list(db.scalars(statement).all())


def get_by_contribution_and_level(
    db: Session,
    contribution_id: int,
    level: str
) -> Explanation | None:
    statement = select(Explanation).where(
        Explanation.contribution_id == contribution_id,
        Explanation.level == level
    )
    return db.scalar(statement)


def create(
    db: Session,
    explanation: Explanation
) -> Explanation:
    db.add(explanation)
    db.flush()
    db.refresh(explanation)

    return explanation


def update(
    db: Session,
    explanation: Explanation,
    level: str,
    explanation_text: str,
    key_concepts: str | None
) -> Explanation:
    explanation.level = level
    explanation.explanation_text = explanation_text
    explanation.key_concepts = key_concepts

    db.flush()
    db.refresh(explanation)

    return explanation


def delete(
    db: Session,
    explanation: Explanation
) -> None:
    db.delete(explanation)
    db.flush()
