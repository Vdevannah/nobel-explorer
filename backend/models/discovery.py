from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.connection import Base


class Discovery(Base):
    __tablename__ = "discovery"

    discovery_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    laureate_prize_id: Mapped[int] = mapped_column(
        ForeignKey("laureate_prize.laureate_prize_id"),
        nullable=False
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    significance: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    source_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    laureate_prize = relationship(
        "LaureatePrize",
        back_populates="discoveries"
    )

    applications = relationship(
        "Application",
        back_populates="discovery"
    )

    quiz_questions = relationship(
        "QuizQuestion",
        back_populates="discovery"
    )