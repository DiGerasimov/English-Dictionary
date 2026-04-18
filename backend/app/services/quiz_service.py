import random

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import UserWordProgress, Word
from app.models.progress import LEARNED_THRESHOLD

QUIZ_OPTIONS_COUNT = 6

_STEP_MIN = 3
_STEP_MAX = 10
_P_JITTER = 0.15


def _compute_review_probability(learning_n: int, learned_n: int) -> float:
    """Вероятность показать повторение на след. вопросе.

    Шаг подмешивания step = clamp( learning_n / learned_n, 3, 10 ).
    p_review = 1 / step с небольшим случайным разбросом ±15%, чтобы избежать предсказуемости.
    """
    if learned_n <= 0:
        return 0.0
    if learning_n <= 0:
        return 1.0
    ratio = learning_n / learned_n
    step = max(_STEP_MIN, min(_STEP_MAX, round(ratio)))
    base = 1.0 / step
    jitter = random.uniform(-_P_JITTER, _P_JITTER) * base
    return max(0.0, min(1.0, base + jitter))


def _filter_exclude(words: list[Word], exclude_word_id: int | None) -> list[Word]:
    """Фильтрует слово с указанным id, если после этого хоть что-то осталось."""
    if exclude_word_id is None:
        return words
    filtered = [w for w in words if w.id != exclude_word_id]
    return filtered if filtered else words


async def pick_target_word(
    db: AsyncSession,
    user_id: int,
    category_id: int | None,
    only_unlearned: bool,
    exclude_word_id: int | None = None,
) -> tuple[Word, bool] | None:
    """Выбирает следующее слово для квиза и признак is_review.

    Поведение:
    - Если only_unlearned=True — старая логика: только слова с correct_count < 5, is_review всегда False.
    - Иначе строим два пула: learning (не изученные) и learned (изученные). По формуле
      p_review = 1/clamp(learning/learned, 3, 10) выбираем пул. Подавляем дубль подряд через
      exclude_word_id.
    """
    base_conditions = [
        UserWordProgress.user_id == user_id,
        UserWordProgress.seen.is_(True),
    ]

    stmt = (
        select(Word, UserWordProgress.correct_count)
        .join(UserWordProgress, UserWordProgress.word_id == Word.id)
        .where(and_(*base_conditions))
        .options(selectinload(Word.category), selectinload(Word.forms))
    )
    if category_id is not None:
        stmt = stmt.where(Word.category_id == category_id)

    rows = (await db.execute(stmt)).all()
    if not rows:
        return None

    learning: list[Word] = []
    learned: list[Word] = []
    for word, correct_count in rows:
        if (correct_count or 0) >= LEARNED_THRESHOLD:
            learned.append(word)
        else:
            learning.append(word)

    if only_unlearned:
        pool = _filter_exclude(learning, exclude_word_id)
        if not pool:
            return None
        return random.choice(pool), False

    p_review = _compute_review_probability(len(learning), len(learned))
    use_review = random.random() < p_review if learned else False

    if use_review:
        pool = _filter_exclude(learned, exclude_word_id)
        return random.choice(pool), True

    pool_learning = _filter_exclude(learning, exclude_word_id)
    if pool_learning:
        return random.choice(pool_learning), False
    pool_learned = _filter_exclude(learned, exclude_word_id)
    if pool_learned:
        return random.choice(pool_learned), True
    return None


async def build_distractors(
    db: AsyncSession, target: Word, need: int = QUIZ_OPTIONS_COUNT - 1
) -> list[str]:
    """Собирает русские переводы-дистракторы из той же категории (при нехватке добирает отовсюду)."""
    stmt = (
        select(Word.russian)
        .where(Word.category_id == target.category_id, Word.id != target.id)
        .distinct()
    )
    pool = [r for (r,) in (await db.execute(stmt)).all() if r and r != target.russian]
    random.shuffle(pool)
    result: list[str] = []
    seen: set[str] = {target.russian}
    for r in pool:
        if r in seen:
            continue
        seen.add(r)
        result.append(r)
        if len(result) >= need:
            return result

    if len(result) < need:
        fallback_stmt = (
            select(Word.russian).where(Word.id != target.id).distinct().limit(need * 5)
        )
        extra = [r for (r,) in (await db.execute(fallback_stmt)).all() if r]
        random.shuffle(extra)
        for r in extra:
            if r in seen:
                continue
            seen.add(r)
            result.append(r)
            if len(result) >= need:
                break
    return result


def shuffle_options(correct: str, distractors: list[str]) -> list[str]:
    """Перемешивает список вариантов ответов с правильным."""
    options = [correct] + distractors
    random.shuffle(options)
    return options
