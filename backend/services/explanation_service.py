from sqlalchemy.orm import Session

from backend.models.explanation import Explanation
from backend.repositories import contribution_repository, explanation_repository
from backend.schemas.explanation import ExplanationCreate, ExplanationUpdate
from backend.services.exceptions import ResourceNotFoundError


def _require_contribution(db: Session, contribution_id: int) -> None:
    if contribution_repository.get_by_id(db, contribution_id) is None:
        raise ResourceNotFoundError("Contribution", contribution_id)


def list_explanations(
    db: Session,
    contribution_id: int,
    level: str | None = None,
) -> list[Explanation]:
    _require_contribution(db, contribution_id)
    return explanation_repository.get_by_contribution(db, contribution_id, level)


def get_explanation_by_level(
    db: Session,
    contribution_id: int,
    level: str,
) -> Explanation:
    _require_contribution(db, contribution_id)
    explanation = explanation_repository.get_by_contribution_and_level(
        db, contribution_id, level
    )
    if explanation is None:
        raise ResourceNotFoundError(
            "Explanation", f"contribution={contribution_id}, level={level}"
        )
    return explanation


def create_explanation(db: Session, data: ExplanationCreate) -> Explanation:
    _require_contribution(db, data.contribution_id)
    return explanation_repository.create(db, Explanation(**data.model_dump()))


def update_explanation(
    db: Session,
    explanation_id: int,
    data: ExplanationUpdate,
) -> Explanation:
    explanation = explanation_repository.get_by_id(db, explanation_id)
    if explanation is None:
        raise ResourceNotFoundError("Explanation", explanation_id)
    _require_contribution(db, data.contribution_id)
    explanation.contribution_id = data.contribution_id
    return explanation_repository.update(
        db,
        explanation,
        level=data.level,
        explanation_text=data.explanation_text,
        key_concepts=data.key_concepts,
    )
