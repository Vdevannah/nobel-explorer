from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.connection import Base


class Prize(Base):
    __tablename__ = "prize"

    prize_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    year: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    category_id: Mapped[int] = mapped_column(
        ForeignKey("category.category_id"),
        nullable=False
    )

    category = relationship(
        "Category",
        back_populates="prizes"
    )

    laureate_prizes = relationship(
        "LaureatePrize",
        back_populates="prize"
    )
