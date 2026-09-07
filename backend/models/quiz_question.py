from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.connection import Base


class QuizQuestion(Base):
    __tablename__ = "quiz_question"
    __table_args__ = (
        CheckConstraint(
            "level IN ('Simple', 'Explore', 'Advanced', 'Expert')",
            name="ck_quiz_question_level",
        ),
        CheckConstraint(
            "correct_answer IN ('A', 'B', 'C', 'D')",
            name="ck_quiz_question_correct_answer",
        ),
        Index("ix_quiz_question_contribution_id", "contribution_id"),
    )

    question_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    contribution_id: Mapped[int] = mapped_column(
        ForeignKey("contribution.contribution_id"),
        nullable=False
    )

    level: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    question: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    choice_a: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    choice_b: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    choice_c: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    choice_d: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    correct_answer: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )

    answer_explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    contribution = relationship(
        "Contribution",
        back_populates="quiz_questions"
    )
