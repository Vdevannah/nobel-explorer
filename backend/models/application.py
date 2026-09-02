from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.connection import Base


class Application(Base):
    __tablename__ = "application"

    application_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    discovery_id: Mapped[int] = mapped_column(
        ForeignKey("discovery.discovery_id"),
        nullable=False
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    source_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True
    )

    source_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    discovery = relationship(
        "Discovery",
        back_populates="applications"
    )

    explanations = relationship(
        "Explanation",
        back_populates="application"
    )