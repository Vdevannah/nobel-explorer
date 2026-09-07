from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.schemas.connection import ConnectionResponse
from backend.schemas.contribution import ContributionDetailResponse
from backend.schemas.explanation import ExplanationLevel, ExplanationResponse
from backend.schemas.quiz_question import QuizQuestionPublicResponse
from backend.services import (
    connection_service,
    contribution_service,
    explanation_service,
    quiz_question_service,
)


router = APIRouter(prefix="/contributions", tags=["Educational Content"])


@router.get(
    "/{contribution_id}",
    response_model=ContributionDetailResponse,
    summary="Get contribution details",
    responses={404: {"description": "Contribution not found"}},
)
def get_contribution(
    contribution_id: int = Path(
        description="Nobel Explorer internal contribution database ID"
    ),
    db: Session = Depends(get_db),
):
    return contribution_service.get_contribution(db, contribution_id)


@router.get(
    "/{contribution_id}/connections",
    response_model=list[ConnectionResponse],
    summary="List educational connections for a contribution",
    responses={404: {"description": "Contribution not found"}},
)
def list_connections(
    contribution_id: int = Path(
        description="Nobel Explorer internal contribution database ID"
    ),
    db: Session = Depends(get_db),
):
    return connection_service.list_connections(db, contribution_id)


@router.get(
    "/{contribution_id}/explanations",
    response_model=list[ExplanationResponse],
    summary="List learning-level explanations for a contribution",
    responses={404: {"description": "Contribution not found"}},
)
def list_explanations(
    contribution_id: int = Path(
        description="Nobel Explorer internal contribution database ID"
    ),
    level: ExplanationLevel | None = Query(
        default=None,
        description="Optional learning-level filter",
    ),
    db: Session = Depends(get_db),
):
    return explanation_service.list_explanations(db, contribution_id, level)


@router.get(
    "/{contribution_id}/explanations/{level}",
    response_model=ExplanationResponse,
    summary="Get one learning-level explanation",
    responses={404: {"description": "Contribution or explanation not found"}},
)
def get_explanation(
    contribution_id: int = Path(
        description="Nobel Explorer internal contribution database ID"
    ),
    level: ExplanationLevel = Path(description="Approved learning level"),
    db: Session = Depends(get_db),
):
    return explanation_service.get_explanation_by_level(
        db, contribution_id, level
    )


@router.get(
    "/{contribution_id}/quiz",
    response_model=list[QuizQuestionPublicResponse],
    summary="List public quiz questions for a contribution",
    description="Correct answers and answer explanations are intentionally omitted.",
    responses={404: {"description": "Contribution not found"}},
)
def list_quiz_questions(
    contribution_id: int = Path(
        description="Nobel Explorer internal contribution database ID"
    ),
    level: ExplanationLevel | None = Query(
        default=None,
        description="Optional learning-level filter",
    ),
    db: Session = Depends(get_db),
):
    return quiz_question_service.list_quiz_questions(
        db, contribution_id, level
    )
