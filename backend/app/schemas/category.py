from pydantic import BaseModel


class CategoryOut(BaseModel):
    id: int
    slug: str
    name_ru: str
    name_en: str
    icon: str
    description: str
    order_index: int
    words_count: int = 0
    seen_count: int = 0
    learned_count: int = 0
    quiz_ready_count: int = 0
    new_available_count: int = 0
    is_pinned: bool = False

    model_config = {"from_attributes": True}
