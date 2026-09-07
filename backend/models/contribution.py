from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.connection import Base


class Contribution(Base):
    __tablename__ = "contribution"
    __table_args__ = (
        CheckConstraint(
            "contribution_type IN ('NOBEL_LINKED', 'BEYOND_NOBEL')",
            name="ck_contribution_type",
        ),
        CheckConstraint(
            "(contribution_type = 'NOBEL_LINKED' AND laureate_prize_id IS NOT NULL) "
            "OR (contribution_type = 'BEYOND_NOBEL' AND laureate_prize_id IS NULL)",
            name="ck_contribution_prize_link",
        ),
        UniqueConstraint(
            "laureate_id",
            "contribution_type",
            "title",
            name="uq_contribution_laureate_type_title",
        ),
        Index("ix_contribution_laureate_id", "laureate_id"),
        Index("ix_contribution_laureate_prize_id", "laureate_prize_id"),
    )

    contribution_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    laureate_id: Mapped[int] = mapped_column(
        ForeignKey("laureate.laureate_id"),
        nullable=False,
    )
    laureate_prize_id: Mapped[int | None] = mapped_column(
        ForeignKey("laureate_prize.laureate_prize_id"),
        nullable=True,
    )
    contribution_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    significance: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    laureate = relationship("Laureate", back_populates="contributions")
    laureate_prize = relationship("LaureatePrize", back_populates="contributions")
    explanations = relationship("Explanation", back_populates="contribution")
    connections = relationship("Connection", back_populates="contribution")
    quiz_questions = relationship("QuizQuestion", back_populates="contribution")
