"""Идемпотентный сидинг базовых категорий (25 штук, по смыслу компактные)."""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.category import Category

CATEGORIES: list[dict[str, str | int]] = [
    {"slug": "fruits", "name_ru": "Фрукты и ягоды", "name_en": "Fruits & Berries", "icon": "🍎",
     "description": "Свежие, сушёные, косточковые — вкусные слова", "order_index": 10},
    {"slug": "vegetables", "name_ru": "Овощи", "name_en": "Vegetables", "icon": "🥕",
     "description": "Корнеплоды, зелень и всё с грядки", "order_index": 20},
    {"slug": "animals", "name_ru": "Животные", "name_en": "Animals", "icon": "🐾",
     "description": "Домашние и дикие животные", "order_index": 30},
    {"slug": "birds", "name_ru": "Птицы", "name_en": "Birds", "icon": "🦜",
     "description": "Птицы вокруг нас и не только", "order_index": 40},
    {"slug": "colors", "name_ru": "Цвета", "name_en": "Colors", "icon": "🎨",
     "description": "Основные цвета и оттенки", "order_index": 50},
    {"slug": "numbers", "name_ru": "Числа", "name_en": "Numbers", "icon": "🔢",
     "description": "Количественные и порядковые числительные", "order_index": 60},
    {"slug": "family", "name_ru": "Семья", "name_en": "Family", "icon": "👨‍👩‍👧",
     "description": "Родственники и близкие", "order_index": 70},
    {"slug": "body", "name_ru": "Тело", "name_en": "Body", "icon": "🧍",
     "description": "Части тела и их описания", "order_index": 80},
    {"slug": "clothes", "name_ru": "Одежда", "name_en": "Clothes", "icon": "👕",
     "description": "Одежда, обувь, аксессуары", "order_index": 90},
    {"slug": "house", "name_ru": "Дом", "name_en": "House", "icon": "🏠",
     "description": "Комнаты, мебель, предметы быта", "order_index": 100},
    {"slug": "kitchen", "name_ru": "Кухня", "name_en": "Kitchen", "icon": "🍳",
     "description": "Посуда, техника, приборы", "order_index": 110},
    {"slug": "drinks", "name_ru": "Напитки", "name_en": "Drinks", "icon": "🥤",
     "description": "От воды до коктейлей", "order_index": 120},
    {"slug": "weather", "name_ru": "Погода", "name_en": "Weather", "icon": "⛅",
     "description": "Осадки, температура, явления", "order_index": 130},
    {"slug": "time", "name_ru": "Время и даты", "name_en": "Time & Dates", "icon": "⏰",
     "description": "Часы, дни, месяцы, сезоны", "order_index": 140},
    {"slug": "travel", "name_ru": "Путешествия", "name_en": "Travel", "icon": "✈️",
     "description": "Аэропорт, отель, документы", "order_index": 150},
    {"slug": "transport", "name_ru": "Транспорт", "name_en": "Transport", "icon": "🚗",
     "description": "Все виды передвижения", "order_index": 160},
    {"slug": "it", "name_ru": "IT и программирование", "name_en": "IT & Programming", "icon": "💻",
     "description": "Разработка, сервера, облака", "order_index": 170},
    {"slug": "business", "name_ru": "Бизнес", "name_en": "Business", "icon": "💼",
     "description": "Работа, переговоры, документы", "order_index": 180},
    {"slug": "emotions", "name_ru": "Эмоции и чувства", "name_en": "Emotions & Feelings", "icon": "😊",
     "description": "Настроение, состояния, отношения", "order_index": 190},
    {"slug": "school", "name_ru": "Школа и образование", "name_en": "School & Education", "icon": "🎓",
     "description": "Уроки, предметы, экзамены", "order_index": 200},
    {"slug": "sports", "name_ru": "Спорт", "name_en": "Sports", "icon": "⚽",
     "description": "Виды спорта и инвентарь", "order_index": 210},
    {"slug": "verbs-basic", "name_ru": "Базовые глаголы", "name_en": "Basic Verbs", "icon": "⚡",
     "description": "Самые употребимые глаголы с формами", "order_index": 220},
    {"slug": "adjectives-basic", "name_ru": "Базовые прилагательные", "name_en": "Basic Adjectives", "icon": "✨",
     "description": "Описательные слова на каждый день", "order_index": 230},
    {"slug": "pronouns", "name_ru": "Местоимения", "name_en": "Pronouns", "icon": "🔤",
     "description": "Личные, притяжательные, указательные", "order_index": 240},
    {"slug": "prepositions", "name_ru": "Предлоги", "name_en": "Prepositions", "icon": "🔗",
     "description": "Места, времени, направления", "order_index": 250},
    {"slug": "base", "name_ru": "Главная база", "name_en": "Base", "icon": "⭐",
     "description": "Самые важные слова для построения предложений", "order_index": 260},
]


async def seed(db: AsyncSession) -> None:
    """Upsert категорий по slug: создаёт новые, обновляет существующие."""
    existing_result = await db.execute(select(Category))
    existing = {c.slug: c for c in existing_result.scalars().all()}

    created, updated = 0, 0
    for item in CATEGORIES:
        slug = item["slug"]
        if slug in existing:
            cat = existing[slug]
            changed = False
            for field in ("name_ru", "name_en", "icon", "description", "order_index"):
                if getattr(cat, field) != item[field]:
                    setattr(cat, field, item[field])
                    changed = True
            if changed:
                updated += 1
        else:
            db.add(Category(**item))
            created += 1

    if created or updated:
        await db.commit()
    print(f"[seed:categories] создано {created}, обновлено {updated}, в списке {len(CATEGORIES)}")


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
