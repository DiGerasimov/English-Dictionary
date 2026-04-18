from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import QuizAttempt, User, UserWordProgress, Word
from app.models.progress import LEARNED_THRESHOLD
from app.schemas.quiz import QuizAnswerIn, QuizAnswerOut, QuizQuestionOut
from app.schemas.word import WordCategoryMini, WordFormOut, WordFormProgressOut, WordOut, WordProgressOut
from app.services.activation_service import ensure_active_words
from app.services.progress_service import register_quiz_result
from app.services.quiz_service import build_distractors, pick_target_word, shuffle_options

router = APIRouter(prefix="/quiz", tags=["quiz"])


def _word_to_out(word: Word, progress: UserWordProgress | None) -> WordOut:
    return WordOut(
        id=word.id,
        english=word.english,
        russian=word.russian,
        description=word.description,
        transcription_ipa=word.transcription_ipa,
        transcription_ru=word.transcription_ru,
        difficulty=word.difficulty,
        part_of_speech=word.part_of_speech,
        category=WordCategoryMini.model_validate(word.category),
        forms=[
            WordFormOut(
                id=f.id,
                form_type=f.form_type,
                english=f.english,
                russian=f.russian,
                transcription_ipa=f.transcription_ipa,
                transcription_ru=f.transcription_ru,
                progress=WordFormProgressOut(),
            )
            for f in word.forms
        ],
        progress=WordProgressOut(
            seen=bool(progress.seen) if progress else False,
            correct_count=progress.correct_count if progress else 0,
            incorrect_count=progress.incorrect_count if progress else 0,
            is_learned=bool(progress and progress.correct_count >= LEARNED_THRESHOLD),
            first_seen_at=progress.first_seen_at if progress else None,
            last_seen_at=progress.last_seen_at if progress else None,
            learned_at=progress.learned_at if progress else None,
        ),
    )


@router.get("/next", response_model=QuizQuestionOut)
async def next_question(
    scope: str = Query("all", pattern="^(all|category)$"),
    category_id: int | None = Query(None),
    only_unlearned: bool = Query(True),
    exclude_word_id: int | None = Query(None, description="ID последнего слова — чтобы исключить его из выбора"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuizQuestionOut:
    """Возвращает следующий вопрос квиза: слово + 6 вариантов ответа и флаг is_review."""
    picked = await pick_target_word(
        db,
        user_id=user.id,
        category_id=category_id if scope == "category" else None,
        only_unlearned=only_unlearned,
        exclude_word_id=exclude_word_id,
    )
    if not picked:
        raise HTTPException(
            status_code=404,
            detail=(
                "Нет доступных слов для квиза. "
                "Откройте несколько карточек в режиме «Изучение», чтобы добавить их в выборку."
            ),
        )

    target, is_review = picked
    distractors = await build_distractors(db, target)
    options = shuffle_options(target.russian, distractors)

    progress_stmt = select(UserWordProgress).where(
        UserWordProgress.user_id == user.id, UserWordProgress.word_id == target.id
    )
    progress = (await db.execute(progress_stmt)).scalar_one_or_none()

    return QuizQuestionOut(
        word=_word_to_out(target, progress),
        options=options,
        is_review=is_review,
    )


@router.post("/answer", response_model=QuizAnswerOut)
async def submit_answer(
    data: QuizAnswerIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuizAnswerOut:
    """Проверяет ответ, обновляет счётчики прогресса и пишет QuizAttempt.

    Для уже изученных слов (correct_count >= 5) счётчики correct/incorrect НЕ увеличиваются —
    это режим «повторения», правильность только для UX-фидбэка и статистики QuizAttempt.
    """
    stmt = (
        select(Word)
        .options(selectinload(Word.category), selectinload(Word.forms))
        .where(Word.id == data.word_id)
    )
    word = (await db.execute(stmt)).scalar_one_or_none()
    if not word:
        raise HTTPException(status_code=404, detail="Слово не найдено")

    is_correct = data.selected.strip().lower() == word.russian.strip().lower()

    existing_stmt = select(UserWordProgress).where(
        UserWordProgress.user_id == user.id, UserWordProgress.word_id == word.id
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    was_learned = bool(existing and existing.correct_count >= LEARNED_THRESHOLD)

    if was_learned:
        progress = existing
        progress.last_seen_at = datetime.now(timezone.utc)
    else:
        progress = await register_quiz_result(db, user.id, word.id, is_correct)

    attempt = QuizAttempt(
        user_id=user.id,
        word_id=word.id,
        category_id=word.category_id,
        is_correct=is_correct,
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(progress)

    # Если слово только что стало изученным — открываем новое активное слово в этой категории
    if not was_learned and is_correct and progress.correct_count >= LEARNED_THRESHOLD:
        await ensure_active_words(db, user, category_id=word.category_id)

    return QuizAnswerOut(
        is_correct=is_correct,
        correct_answer=word.russian,
        word=_word_to_out(word, progress),
        is_review=was_learned,
    )
