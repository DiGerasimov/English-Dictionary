import enum

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FormType(str, enum.Enum):
    base = "base"
    past_simple = "past_simple"
    past_participle = "past_participle"
    present_participle = "present_participle"
    third_person = "third_person"
    plural = "plural"
    comparative = "comparative"
    superlative = "superlative"


class WordForm(Base):
    __tablename__ = "word_forms"

    id: Mapped[int] = mapped_column(primary_key=True)
    word_id: Mapped[int] = mapped_column(
        ForeignKey("words.id", ondelete="CASCADE"), index=True, nullable=False
    )
    form_type: Mapped[FormType] = mapped_column(Enum(FormType, name="form_type"), nullable=False)
    english: Mapped[str] = mapped_column(String(128), nullable=False)
    russian: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    transcription_ipa: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    transcription_ru: Mapped[str] = mapped_column(String(128), default="", nullable=False)

    word: Mapped["Word"] = relationship(back_populates="forms")  # noqa: F821
