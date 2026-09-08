from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.schemas.quiz_question import QuizAnswerCheckRequest, QuizAnswerReviewResponse
from backend.services import quiz_question_service


router = APIRouter(prefix="/quiz-questions", tags=["Educational Content"])


@router.post(
    "/{question_id}/check",
    response_model=QuizAnswerReviewResponse,
    summary="Check a submitted quiz answer",
    responses={404: {"description": "Quiz question not found"}},
)
def check_quiz_answer(
    payload: QuizAnswerCheckRequest,
    question_id: int = Path(
        description="Nobel Explorer internal quiz question database ID"
    ),
    db: Session = Depends(get_db),
):
    return quiz_question_service.check_answer(
        db, question_id, payload.selected_answer
    )
