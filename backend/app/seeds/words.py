"""Сидинг слов из JSON-файлов в backend/words/.

Идея:
  1. Для каждой категории в БД проверяем наличие файла <slug>.json в WORDS_DIR.
     Если файла нет — создаём пустой шаблон (чтобы было куда класть слова).
  2. Загружаем все существующие JSON-ы и делаем upsert:
     - Слово ищется по паре (category_id, english). Если нет — создаётся, если есть — обновляется.
     - Формы (WordForm) обновляются/создаются/удаляются по (word_id, form_type).
  3. Лог: сколько создано/обновлено, сколько скелетных файлов добавлено.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.category import Category
from app.models.word import Difficulty, PartOfSpeech, Word
from app.models.word_form import FormType, WordForm

WORDS_DIR = Path(__file__).resolve().parents[2] / "words"


def ensure_skeleton_files(slugs: list[str]) -> int:
    """Создаёт пустые JSON-шаблоны для категорий, у которых ещё нет файла."""
    WORDS_DIR.mkdir(parents=True, exist_ok=True)
    created = 0
    for slug in slugs:
        path = WORDS_DIR / f"{slug}.json"
        if not path.exists():
            path.write_text(
                json.dumps({"slug": slug, "words": []}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            created += 1
    return created


def load_all_payloads() -> list[dict[str, Any]]:
    """Читает все валидные JSON-файлы из WORDS_DIR."""
    payloads: list[dict[str, Any]] = []
    if not WORDS_DIR.exists():
        return payloads
    for path in sorted(WORDS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"[seed:words] пропуск {path.name}: JSON ошибка — {e}")
            continue
        if not isinstance(data, dict) or "slug" not in data or "words" not in data:
            print(f"[seed:words] пропуск {path.name}: нет slug/words")
            continue
        payloads.append(data)
    return payloads


def _sanitize(value: str | None, fallback: str = "") -> str:
    return (value or fallback).strip()


async def upsert_word(db: AsyncSession, category: Category, payload: dict[str, Any]) -> tuple[bool, bool]:
    """Создаёт или обновляет одно слово + его формы. Возвращает (created, updated)."""
    english = _sanitize(payload.get("english")).lower()
    russian = _sanitize(payload.get("russian"))
    if not english or not russian:
        return False, False

    existing_stmt = (
        select(Word)
        .options(selectinload(Word.forms))
        .where(Word.category_id == category.id, Word.english == english)
    )
    word = (await db.execute(existing_stmt)).scalar_one_or_none()

    try:
        difficulty = Difficulty(payload.get("difficulty", "easy"))
    except ValueError:
        difficulty = Difficulty.easy
    try:
        part_of_speech = PartOfSpeech(payload.get("part_of_speech", "noun"))
    except ValueError:
        part_of_speech = PartOfSpeech.noun

    fields = {
        "russian": russian,
        "description": _sanitize(payload.get("description")),
        "transcription_ipa": _sanitize(payload.get("transcription_ipa")),
        "transcription_ru": _sanitize(payload.get("transcription_ru")),
        "difficulty": difficulty,
        "part_of_speech": part_of_speech,
    }

    created = updated = False

    if word is None:
        word = Word(category_id=category.id, english=english, **fields)
        db.add(word)
        await db.flush()
        created = True
    else:
        for k, v in fields.items():
            if getattr(word, k) != v:
                setattr(word, k, v)
                updated = True

    await _sync_forms(db, word, payload.get("forms") or [])

    return created, updated


async def _sync_forms(db: AsyncSession, word: Word, forms_payload: list[dict[str, Any]]) -> None:
    """Синхронизация форм слова: ключ — (word_id, form_type)."""
    existing_stmt = select(WordForm).where(WordForm.word_id == word.id)
    existing = {f.form_type: f for f in (await db.execute(existing_stmt)).scalars().all()}

    seen_types: set[FormType] = set()
    for item in forms_payload:
        try:
            form_type = FormType(item.get("form_type"))
        except ValueError:
            continue
        seen_types.add(form_type)

        english = _sanitize(item.get("english"))
        if not english:
            continue
        fields = {
            "english": english,
            "russian": _sanitize(item.get("russian")),
            "transcription_ipa": _sanitize(item.get("transcription_ipa")),
            "transcription_ru": _sanitize(item.get("transcription_ru")),
        }

        if form_type in existing:
            form = existing[form_type]
            for k, v in fields.items():
                if getattr(form, k) != v:
                    setattr(form, k, v)
        else:
            db.add(WordForm(word_id=word.id, form_type=form_type, **fields))

    for form_type, form in existing.items():
        if form_type not in seen_types:
            await db.delete(form)


async def seed(db: AsyncSession) -> None:
    """Главный шаг сидинга слов."""
    cats_stmt = select(Category)
    categories = {c.slug: c for c in (await db.execute(cats_stmt)).scalars().all()}

    skeletons = ensure_skeleton_files(list(categories.keys()))
    if skeletons:
        print(f"[seed:words] создано пустых JSON-шаблонов: {skeletons}")

    payloads = load_all_payloads()
    total_created = total_updated = total_skipped = 0

    for data in payloads:
        slug = data["slug"]
        category = categories.get(slug)
        if not category:
            print(f"[seed:words] предупреждение: категория '{slug}' не найдена, пропуск {len(data.get('words', []))} слов")
            total_skipped += len(data.get("words", []))
            continue

        for word_payload in data.get("words", []):
            created, updated = await upsert_word(db, category, word_payload)
            if created:
                total_created += 1
            elif updated:
                total_updated += 1

    await db.commit()
    print(
        f"[seed:words] создано {total_created}, обновлено {total_updated}, "
        f"пропущено {total_skipped}, файлов {len(payloads)}"
    )


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
