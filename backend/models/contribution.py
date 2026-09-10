from sqlalchemy import CheckConstraint, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.connection import Base


class Contribution(Base):
    __tablename__ = "contribution"
    __table_args__ = (
        CheckConstraint(
            "contribution_type IN ('NOBEL_LINKED', 'BEYOND_NOBEL')",
            name="ck_contribution_type",
        ),
    )

    contribution_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contribution_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    significance: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    credited_laureates = relationship(
        "ContributionLaureate", back_populates="contribution",
        cascade="all, delete-orphan", order_by="ContributionLaureate.laureate_id",
    )

    # Derived compatibility fields only; attribution is stored in the junction.
    @property
    def laureate_id(self):
        return min(self.credited_laureates, key=lambda credit: credit.laureate_id).laureate_id

    @property
    def laureate_prize_id(self):
        return min(self.credited_laureates, key=lambda credit: credit.laureate_id).laureate_prize_id

    explanations = relationship("Explanation", back_populates="contribution")
    connections = relationship("Connection", back_populates="contribution")
    quiz_questions = relationship("QuizQuestion", back_populates="contribution")
