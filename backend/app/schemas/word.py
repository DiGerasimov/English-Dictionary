from datetime import datetime

from pydantic import BaseModel

from app.models.word import Difficulty, PartOfSpeech
from app.models.word_form import FormType


class WordFormProgressOut(BaseModel):
    correct_count: int = 0
    incorrect_count: int = 0
    is_learned: bool = False


class WordFormOut(BaseModel):
    id: int
    form_type: FormType
    english: str
    russian: str
    transcription_ipa: str
    transcription_ru: str
    progress: WordFormProgressOut = WordFormProgressOut()

    model_config = {"from_attributes": True}


class WordProgressOut(BaseModel):
    seen: bool = False
    correct_count: int = 0
    incorrect_count: int = 0
    view_count: int = 0
    is_learned: bool = False
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    learned_at: datetime | None = None


class WordCategoryMini(BaseModel):
    id: int
    slug: str
    name_ru: str
    icon: str

    model_config = {"from_attributes": True}


class WordOut(BaseModel):
    id: int
    english: str
    russian: str
    description: str
    transcription_ipa: str
    transcription_ru: str
    difficulty: Difficulty
    part_of_speech: PartOfSpeech
    category: WordCategoryMini
    forms: list[WordFormOut] = []
    progress: WordProgressOut = WordProgressOut()

    model_config = {"from_attributes": True}


class WordListOut(BaseModel):
    items: list[WordOut]
    next_cursor: int | None = None
