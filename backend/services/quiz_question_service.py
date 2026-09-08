from sqlalchemy.orm import Session

from backend.models.quiz_question import QuizQuestion
from backend.repositories import contribution_repository, quiz_question_repository
from backend.schemas.quiz_question import (
    QuizAnswerReviewResponse,
    QuizQuestionCreate,
    QuizQuestionUpdate,
)
from backend.services.exceptions import ResourceNotFoundError


def _require_contribution(db: Session, contribution_id: int) -> None:
    if contribution_repository.get_by_id(db, contribution_id) is None:
        raise ResourceNotFoundError("Contribution", contribution_id)


def list_quiz_questions(
    db: Session,
    contribution_id: int,
    level: str | None = None,
) -> list[QuizQuestion]:
    _require_contribution(db, contribution_id)
    return quiz_question_repository.get_by_contribution(
        db, contribution_id, level
    )


def check_answer(
    db: Session,
    question_id: int,
    selected_answer: str,
) -> QuizAnswerReviewResponse:
    question = quiz_question_repository.get_by_id(db, question_id)
    if question is None:
        raise ResourceNotFoundError("QuizQuestion", question_id)
    return QuizAnswerReviewResponse(
        question_id=question.question_id,
        correct=selected_answer == question.correct_answer,
        correct_answer=question.correct_answer,
        answer_explanation=question.answer_explanation,
    )


def create_quiz_question(db: Session, data: QuizQuestionCreate) -> QuizQuestion:
    _require_contribution(db, data.contribution_id)
    return quiz_question_repository.create(db, QuizQuestion(**data.model_dump()))


def update_quiz_question(
    db: Session,
    question_id: int,
    data: QuizQuestionUpdate,
) -> QuizQuestion:
    question = quiz_question_repository.get_by_id(db, question_id)
    if question is None:
        raise ResourceNotFoundError("QuizQuestion", question_id)
    _require_contribution(db, data.contribution_id)
    question.contribution_id = data.contribution_id
    return quiz_question_repository.update(
        db,
        question,
        level=data.level,
        question_text=data.question,
        choice_a=data.choice_a,
        choice_b=data.choice_b,
        choice_c=data.choice_c,
        choice_d=data.choice_d,
        correct_answer=data.correct_answer,
        answer_explanation=data.answer_explanation,
    )
