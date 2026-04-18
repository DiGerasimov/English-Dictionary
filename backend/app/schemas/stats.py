from datetime import date

from pydantic import BaseModel


class OverviewOut(BaseModel):
    learned_today: int
    learned_yesterday: int
    learned_total: int
    seen_total: int
    correct_today: int
    incorrect_today: int
    correct_today_words: int
    incorrect_today_words: int
    accuracy_total: float
    streak_days: int


class TimelinePoint(BaseModel):
    date: date
    correct: int
    incorrect: int
    learned: int


class TimelineOut(BaseModel):
    points: list[TimelinePoint]


class CategoryStatOut(BaseModel):
    category_id: int
    slug: str
    name_ru: str
    icon: str
    words_count: int
    seen_count: int
    learned_count: int
    correct: int
    incorrect: int
    accuracy: float


class ByCategoryOut(BaseModel):
    items: list[CategoryStatOut]
