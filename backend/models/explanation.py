from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.connection import Base


class Explanation(Base):
    __tablename__ = "explanation"

    __table_args__ = (
        UniqueConstraint(
        "application_id",
        "level",
        name="uq_explanation_application_level"
    ),
)

    explanation_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    application_id: Mapped[int] = mapped_column(
        ForeignKey("application.application_id"),
        nullable=False
    )

    level: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    explanation_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    key_concepts: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    application = relationship(
        "Application",
        back_populates="explanations"
    )