from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.quiz_question import QuizQuestion


def get_by_id(
    db: Session,
    question_id: int
) -> QuizQuestion | None:
    statement = select(QuizQuestion).where(
        QuizQuestion.question_id == question_id
    )
    return db.scalar(statement)


def get_by_contribution(
    db: Session,
    contribution_id: int,
    level: str | None = None,
) -> list[QuizQuestion]:
    statement = select(QuizQuestion).where(
        QuizQuestion.contribution_id == contribution_id
    )
    if level is not None:
        statement = statement.where(QuizQuestion.level == level)
    statement = statement.order_by(QuizQuestion.question_id)
    return list(db.scalars(statement).all())


def get_by_contribution_and_level(
    db: Session,
    contribution_id: int,
    level: str
) -> list[QuizQuestion]:
    statement = select(QuizQuestion).where(
        QuizQuestion.contribution_id == contribution_id,
        QuizQuestion.level == level
    )
    return list(db.scalars(statement).all())


def get_by_contribution_and_question(
    db: Session,
    contribution_id: int,
    question_text: str,
) -> QuizQuestion | None:
    statement = select(QuizQuestion).where(
        QuizQuestion.contribution_id == contribution_id,
        QuizQuestion.question == question_text,
    )
    return db.scalar(statement)


def create(
    db: Session,
    question: QuizQuestion
) -> QuizQuestion:
    db.add(question)
    db.flush()
    db.refresh(question)

    return question


def update(
    db: Session,
    question: QuizQuestion,
    level: str,
    question_text: str,
    choice_a: str,
    choice_b: str,
    choice_c: str,
    choice_d: str,
    correct_answer: str,
    answer_explanation: str | None
) -> QuizQuestion:
    question.level = level
    question.question = question_text
    question.choice_a = choice_a
    question.choice_b = choice_b
    question.choice_c = choice_c
    question.choice_d = choice_d
    question.correct_answer = correct_answer
    question.answer_explanation = answer_explanation

    db.flush()
    db.refresh(question)

    return question


def delete(
    db: Session,
    question: QuizQuestion
) -> None:
    db.delete(question)
    db.flush()
