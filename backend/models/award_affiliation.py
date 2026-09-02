from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.connection import Base


class AwardAffiliation(Base):
    __tablename__ = "award_affiliation"

    __table_args__ = (
        UniqueConstraint(
            "laureate_prize_id",
            "institution_id",
            name="uq_award_affiliation"
        ),
    )

    award_affiliation_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    laureate_prize_id: Mapped[int] = mapped_column(
        ForeignKey("laureate_prize.laureate_prize_id"),
        nullable=False
    )

    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institution.institution_id"),
        nullable=False
    )

    laureate_prize = relationship(
        "LaureatePrize",
        back_populates="award_affiliations"
    )

    institution = relationship(
        "Institution",
        back_populates="award_affiliations"
    )