from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name_ru: Mapped[str] = mapped_column(String(128), nullable=False)
    name_en: Mapped[str] = mapped_column(String(128), nullable=False)
    icon: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    description: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    words: Mapped[list["Word"]] = relationship(  # noqa: F821
        back_populates="category", cascade="all, delete-orphan"
    )
