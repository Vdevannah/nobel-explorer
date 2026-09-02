from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.connection import Base


class LaureatePrize(Base):
    __tablename__ = "laureate_prize"

    __table_args__ = (
    UniqueConstraint(
        "laureate_id",
        "prize_id",
        name="uq_laureate_prize"
    ),
)

    laureate_prize_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    laureate_id: Mapped[int] = mapped_column(
        ForeignKey("laureate.laureate_id"),
        nullable=False
    )

    prize_id: Mapped[int] = mapped_column(
        ForeignKey("prize.prize_id"),
        nullable=False
    )

    prize_share: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True
    )

    laureate = relationship(
        "Laureate",
        back_populates="laureate_prizes"
    )

    prize = relationship(
        "Prize",
        back_populates="laureate_prizes"
    )

    discoveries = relationship(
        "Discovery",
        back_populates="laureate_prize"
    )

    award_affiliations = relationship(
    "AwardAffiliation",
    back_populates="laureate_prize"
)