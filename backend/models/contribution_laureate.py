from sqlalchemy import ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.connection import Base


class ContributionLaureate(Base):
    __tablename__ = "contribution_laureate"
    __table_args__ = (
        Index("ix_contribution_laureate_laureate_id", "laureate_id"),
        Index("ix_contribution_laureate_award_id", "laureate_prize_id"),
    )

    contribution_id: Mapped[int] = mapped_column(
        ForeignKey("contribution.contribution_id"), primary_key=True,
    )
    laureate_id: Mapped[int] = mapped_column(
        ForeignKey("laureate.laureate_id"), primary_key=True,
    )
    laureate_prize_id: Mapped[int | None] = mapped_column(
        ForeignKey("laureate_prize.laureate_prize_id"), nullable=True,
    )

    contribution = relationship("Contribution", back_populates="credited_laureates")
    laureate = relationship("Laureate", back_populates="contribution_attributions")
    laureate_prize = relationship("LaureatePrize", back_populates="contribution_attributions")

    @property
    def name(self):
        return self.laureate.full_name

    @property
    def image_url(self):
        return self.laureate.image_url
