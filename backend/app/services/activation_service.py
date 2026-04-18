from datetime import datetime, timezone

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserWordProgress, Word
from app.models.progress import LEARNED_THRESHOLD
from app.models.word import Difficulty


# Вес сложности для сортировки: сначала лёгкие, затем средние, затем сложные
_DIFFICULTY_ORDER = case(
    (Word.difficulty == Difficulty.easy, 0),
    (Word.difficulty == Difficulty.medium, 1),
    (Word.difficulty == Difficulty.hard, 2),
    else_=3,
)


async def _activations_today_by_category(
    db: AsyncSession, user_id: int
) -> dict[int, int]:
    """Возвращает карту category_id → число слов, активированных сегодня в ней."""
    today = datetime.now(timezone.utc).date()
    stmt = (
        select(Word.category_id, func.count(UserWordProgress.id))
        .join(UserWordProgress, UserWordProgress.word_id == Word.id)
        .where(
            UserWordProgress.user_id == user_id,
            UserWordProgress.first_seen_at.is_not(None),
            func.date(UserWordProgress.first_seen_at) == today,
        )
        .group_by(Word.category_id)
    )
    rows = (await db.execute(stmt)).all()
    return {cid: int(cnt or 0) for cid, cnt in rows}


async def _active_counts_by_category(
    db: AsyncSession, user_id: int
) -> dict[int, int]:
    """Возвращает карту category_id → количество активных (в банке, не изученных) слов."""
    stmt = (
        select(Word.category_id, func.count(UserWordProgress.id))
        .join(UserWordProgress, UserWordProgress.word_id == Word.id)
        .where(
            UserWordProgress.user_id == user_id,
            UserWordProgress.seen.is_(True),
            UserWordProgress.correct_count < LEARNED_THRESHOLD,
        )
        .group_by(Word.category_id)
    )
    rows = (await db.execute(stmt)).all()
    return {cid: int(cnt or 0) for cid, cnt in rows}


async def _pick_new_words(
    db: AsyncSession,
    user_id: int,
    category_id: int,
    need: int,
) -> list[Word]:
    """Выбирает до `need` ещё не открытых слов категории: сначала лёгкие, внутри уровня — случайно."""
    if need <= 0:
        return []
    stmt = (
        select(Word)
        .outerjoin(
            UserWordProgress,
            and_(
                UserWordProgress.word_id == Word.id,
                UserWordProgress.user_id == user_id,
            ),
        )
        .where(Word.category_id == category_id)
        .where(
            (UserWordProgress.id.is_(None)) | (UserWordProgress.seen.is_(False))
        )
        .order_by(_DIFFICULTY_ORDER.asc(), func.random())
        .limit(need)
    )
    return list((await db.execute(stmt)).scalars().all())


async def _all_category_ids(db: AsyncSession) -> list[int]:
    stmt = select(Word.category_id).distinct()
    return [int(c) for c in (await db.execute(stmt)).scalars().all()]


async def ensure_active_words(
    db: AsyncSession,
    user: User,
    category_id: int | None = None,
    force_daily: bool = False,
) -> int:
    """Открывает недостающие активные слова: слоты и дневной лимит считаются на каждую категорию отдельно.

    При force_daily=True дневной лимит игнорируется — заполняем слоты «как будто новый день».
    Возвращает количество вновь активированных слов.
    """
    slots = max(1, int(user.active_slots or 5))
    daily_cap = max(1, int(user.daily_new_limit or 10))

    active_map = await _active_counts_by_category(db, user.id)
    today_map = {} if force_daily else await _activations_today_by_category(db, user.id)

    if category_id is not None:
        categories = [category_id]
    else:
        categories = await _all_category_ids(db)

    activated_total = 0
    now = datetime.now(timezone.utc)

    for cid in categories:
        current = int(active_map.get(cid, 0))
        today_in_cat = int(today_map.get(cid, 0))
        need_slots = slots - current
        budget = need_slots if force_daily else daily_cap - today_in_cat
        need = min(need_slots, budget)
        if need <= 0:
            continue
        candidates = await _pick_new_words(db, user.id, cid, need)
        for word in candidates:
            progress_stmt = select(UserWordProgress).where(
                UserWordProgress.user_id == user.id,
                UserWordProgress.word_id == word.id,
            )
            progress = (await db.execute(progress_stmt)).scalar_one_or_none()
            if progress is None:
                progress = UserWordProgress(user_id=user.id, word_id=word.id)
                db.add(progress)
            progress.seen = True
            progress.first_seen_at = progress.first_seen_at or now
            progress.last_seen_at = now
            activated_total += 1

    if activated_total:
        await db.commit()
    return activated_total
