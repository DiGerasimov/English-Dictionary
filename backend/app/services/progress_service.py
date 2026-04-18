from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.progress import LEARNED_THRESHOLD, UserWordFormProgress, UserWordProgress


async def get_or_create_word_progress(
    db: AsyncSession, user_id: int, word_id: int
) -> UserWordProgress:
    """Возвращает прогресс пользователя по слову, создаёт при отсутствии."""
    stmt = select(UserWordProgress).where(
        UserWordProgress.user_id == user_id, UserWordProgress.word_id == word_id
    )
    progress = (await db.execute(stmt)).scalar_one_or_none()
    if progress:
        return progress
    progress = UserWordProgress(user_id=user_id, word_id=word_id)
    db.add(progress)
    await db.flush()
    return progress


async def mark_word_seen(db: AsyncSession, user_id: int, word_id: int) -> UserWordProgress:
    """Отмечает слово как просмотренное, обновляет метки времени."""
    progress = await get_or_create_word_progress(db, user_id, word_id)
    now = datetime.now(timezone.utc)
    if not progress.seen:
        progress.seen = True
        progress.first_seen_at = progress.first_seen_at or now
    progress.last_seen_at = now
    await db.commit()
    await db.refresh(progress)
    return progress


async def mark_word_viewed(db: AsyncSession, user_id: int, word_id: int) -> UserWordProgress:
    """Увеличивает счётчик показов карточки (view_count) и обновляет last_seen_at."""
    progress = await get_or_create_word_progress(db, user_id, word_id)
    now = datetime.now(timezone.utc)
    progress.view_count = (progress.view_count or 0) + 1
    if not progress.seen:
        progress.seen = True
        progress.first_seen_at = progress.first_seen_at or now
    progress.last_seen_at = now
    await db.commit()
    await db.refresh(progress)
    return progress


async def register_quiz_result(
    db: AsyncSession, user_id: int, word_id: int, is_correct: bool
) -> UserWordProgress:
    """Обновляет счётчики слова после ответа в квизе."""
    progress = await get_or_create_word_progress(db, user_id, word_id)
    if is_correct:
        progress.correct_count += 1
        if progress.correct_count >= LEARNED_THRESHOLD and progress.learned_at is None:
            progress.learned_at = datetime.now(timezone.utc)
    else:
        progress.incorrect_count += 1
    if not progress.seen:
        progress.seen = True
        progress.first_seen_at = progress.first_seen_at or datetime.now(timezone.utc)
    progress.last_seen_at = datetime.now(timezone.utc)
    return progress


async def get_or_create_form_progress(
    db: AsyncSession, user_id: int, word_form_id: int
) -> UserWordFormProgress:
    stmt = select(UserWordFormProgress).where(
        UserWordFormProgress.user_id == user_id,
        UserWordFormProgress.word_form_id == word_form_id,
    )
    progress = (await db.execute(stmt)).scalar_one_or_none()
    if progress:
        return progress
    progress = UserWordFormProgress(user_id=user_id, word_form_id=word_form_id)
    db.add(progress)
    await db.flush()
    return progress


async def register_form_quiz_result(
    db: AsyncSession, user_id: int, word_form_id: int, is_correct: bool
) -> UserWordFormProgress:
    progress = await get_or_create_form_progress(db, user_id, word_form_id)
    if is_correct:
        progress.correct_count += 1
        if progress.correct_count >= LEARNED_THRESHOLD and progress.learned_at is None:
            progress.learned_at = datetime.now(timezone.utc)
    else:
        progress.incorrect_count += 1
    return progress
