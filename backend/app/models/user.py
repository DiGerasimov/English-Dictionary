from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Настройки обучения: активные слоты на категорию и дневной потолок новых слов
    active_slots: Mapped[int] = mapped_column(
        Integer, default=5, server_default="5", nullable=False
    )
    daily_new_limit: Mapped[int] = mapped_column(
        Integer, default=10, server_default="10", nullable=False
    )
    # Режим «тренировка на слух»: слово на карточке/в квизе блюрится до прослушивания
    voice_mode: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
