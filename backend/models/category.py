from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.connection import Base


class Category(Base):
    __tablename__ = "category"

    __table_args__ = (
        UniqueConstraint("name", name="uq_category_name"),
    )

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(
    String(100),
    nullable=False
)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    prizes = relationship(
        "Prize",
        back_populates="category"
    )
