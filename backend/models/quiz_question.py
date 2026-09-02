from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.connection import Base


class QuizQuestion(Base):
    __tablename__ = "quiz_question"

    question_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    discovery_id: Mapped[int] = mapped_column(
        ForeignKey("discovery.discovery_id"),
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

    discovery = relationship(
        "Discovery",
        back_populates="quiz_questions"
    )