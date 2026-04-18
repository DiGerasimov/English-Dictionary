import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Difficulty(str, enum.Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class PartOfSpeech(str, enum.Enum):
    noun = "noun"
    verb = "verb"
    adjective = "adjective"
    adverb = "adverb"
    pronoun = "pronoun"
    preposition = "preposition"
    conjunction = "conjunction"
    interjection = "interjection"
    phrase = "phrase"


class Word(Base):
    __tablename__ = "words"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    english: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    russian: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    transcription_ipa: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    transcription_ru: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty, name="difficulty"), default=Difficulty.easy, nullable=False, index=True
    )
    part_of_speech: Mapped[PartOfSpeech] = mapped_column(
        Enum(PartOfSpeech, name="part_of_speech"),
        default=PartOfSpeech.noun,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    category: Mapped["Category"] = relationship(back_populates="words")  # noqa: F821
    forms: Mapped[list["WordForm"]] = relationship(  # noqa: F821
        back_populates="word", cascade="all, delete-orphan"
    )
