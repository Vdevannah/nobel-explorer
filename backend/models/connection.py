from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.connection import Base


class Connection(Base):
    __tablename__ = "connection"
    __table_args__ = (
        CheckConstraint(
            "connection_type IN "
            "('APPLICATION', 'EXPERIMENTAL_VALIDATION', 'SCIENTIFIC_LEGACY')",
            name="ck_connection_type",
        ),
        CheckConstraint(
            "related_prize_id IS NULL OR connection_type = 'SCIENTIFIC_LEGACY'",
            name="ck_connection_related_prize",
        ),
        UniqueConstraint(
            "contribution_id",
            "connection_type",
            "title",
            name="uq_connection_contribution_type_title",
        ),
        Index("ix_connection_contribution_id", "contribution_id"),
        Index("ix_connection_related_prize_id", "related_prize_id"),
    )

    connection_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contribution_id: Mapped[int] = mapped_column(
        ForeignKey("contribution.contribution_id"),
        nullable=False,
    )
    connection_type: Mapped[str] = mapped_column(String(40), nullable=False)
    related_prize_id: Mapped[int | None] = mapped_column(
        ForeignKey("prize.prize_id"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    contribution = relationship("Contribution", back_populates="connections")
    related_prize = relationship("Prize", back_populates="related_connections")
