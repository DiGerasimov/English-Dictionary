from pydantic import BaseModel

from app.schemas.word import WordOut


class QuizQuestionOut(BaseModel):
    word: WordOut
    options: list[str]
    is_review: bool = False


class QuizAnswerIn(BaseModel):
    word_id: int
    selected: str


class QuizAnswerOut(BaseModel):
    is_correct: bool
    correct_answer: str
    word: WordOut
    is_review: bool = False
