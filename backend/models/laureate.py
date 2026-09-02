from datetime import date

from sqlalchemy import Boolean, Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.connection import Base


class Laureate(Base):
    __tablename__ = "laureate"

    laureate_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    full_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    laureate_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    birth_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    birth_city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    birth_state: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    birth_country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    gender: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    image_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    featured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    laureate_prizes = relationship(
        "LaureatePrize",
        back_populates="laureate"
    )