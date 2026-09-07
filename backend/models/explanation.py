from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.connection import Base


class Explanation(Base):
    __tablename__ = "explanation"

    __table_args__ = (
        UniqueConstraint(
        "contribution_id",
        "level",
        name="uq_explanation_contribution_level",
        ),
        CheckConstraint(
            "level IN ('Simple', 'Explore', 'Advanced', 'Expert')",
            name="ck_explanation_level",
        ),
        Index("ix_explanation_contribution_id", "contribution_id"),
    )

    explanation_id: Mapped[int] = mapped_column(
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

    explanation_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    key_concepts: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    contribution = relationship(
        "Contribution",
        back_populates="explanations",
    )
