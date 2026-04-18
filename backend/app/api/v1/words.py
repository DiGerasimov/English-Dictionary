from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User, UserWordFormProgress, UserWordProgress, Word
from app.models.progress import LEARNED_THRESHOLD
from app.models.word import Difficulty, PartOfSpeech
from app.schemas.word import (
    WordCategoryMini,
    WordFormOut,
    WordFormProgressOut,
    WordListOut,
    WordOut,
    WordProgressOut,
)
from app.services.activation_service import ensure_active_words
from app.services.progress_service import mark_word_viewed

router = APIRouter(prefix="/words", tags=["words"])


def _word_to_out(
    word: Word,
    wp: UserWordProgress | None,
    forms_progress: dict[int, UserWordFormProgress],
) -> WordOut:
    """Собирает полный DTO слова вместе с прогрессом пользователя."""
    progress = WordProgressOut(
        seen=bool(wp.seen) if wp else False,
        correct_count=wp.correct_count if wp else 0,
        incorrect_count=wp.incorrect_count if wp else 0,
        view_count=wp.view_count if wp else 0,
        is_learned=bool(wp and wp.correct_count >= LEARNED_THRESHOLD),
        first_seen_at=wp.first_seen_at if wp else None,
        last_seen_at=wp.last_seen_at if wp else None,
        learned_at=wp.learned_at if wp else None,
    )

    forms_out: list[WordFormOut] = []
    for form in word.forms:
        fp = forms_progress.get(form.id)
        forms_out.append(
            WordFormOut(
                id=form.id,
                form_type=form.form_type,
                english=form.english,
                russian=form.russian,
                transcription_ipa=form.transcription_ipa,
                transcription_ru=form.transcription_ru,
                progress=WordFormProgressOut(
                    correct_count=fp.correct_count if fp else 0,
                    incorrect_count=fp.incorrect_count if fp else 0,
                    is_learned=bool(fp and fp.correct_count >= LEARNED_THRESHOLD),
                ),
            )
        )

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
        forms=forms_out,
        progress=progress,
    )


async def _load_forms_progress(
    db: AsyncSession, user_id: int, word_ids: list[int]
) -> dict[int, UserWordFormProgress]:
    if not word_ids:
        return {}
    from app.models.word_form import WordForm

    stmt = (
        select(UserWordFormProgress)
        .join(WordForm, WordForm.id == UserWordFormProgress.word_form_id)
        .where(UserWordFormProgress.user_id == user_id, WordForm.word_id.in_(word_ids))
    )
    rows = (await db.execute(stmt)).scalars().all()
    return {r.word_form_id: r for r in rows}


def _apply_multi_filters(
    stmt,
    category_ids: list[int] | None,
    difficulty: list[Difficulty] | None,
    part_of_speech: list[PartOfSpeech] | None,
):
    """Применяет мульти-фильтры к запросу."""
    if category_ids:
        stmt = stmt.where(Word.category_id.in_(category_ids))
    if difficulty:
        stmt = stmt.where(Word.difficulty.in_(difficulty))
    if part_of_speech:
        stmt = stmt.where(Word.part_of_speech.in_(part_of_speech))
    return stmt


@router.get("/active", response_model=WordListOut)
async def list_active_words(
    category_id: list[int] | None = Query(None),
    difficulty: list[Difficulty] | None = Query(None),
    part_of_speech: list[PartOfSpeech] | None = Query(None),
    limit: int = Query(100, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WordListOut:
    """Все seen-слова пользователя (в процессе + изученные как повторение).

    Сортировка:
    - сначала изучаемые (correct_count < 5), затем изученные (как повторение);
    - внутри каждой группы — по view_count ASC (реже показанные выше) и случайность.
    Перед выдачей авто-активирует новые слова до active_slots.
    """
    target_category = category_id[0] if category_id and len(category_id) == 1 else None
    await ensure_active_words(db, user, category_id=target_category)

    stmt = (
        select(Word, UserWordProgress)
        .join(UserWordProgress, UserWordProgress.word_id == Word.id)
        .where(
            UserWordProgress.user_id == user.id,
            UserWordProgress.seen.is_(True),
        )
        .options(selectinload(Word.category), selectinload(Word.forms))
    )
    stmt = _apply_multi_filters(stmt, category_id, difficulty, part_of_speech)

    learning_first = case(
        (UserWordProgress.correct_count < LEARNED_THRESHOLD, 0),
        else_=1,
    )
    stmt = stmt.order_by(
        learning_first.asc(),
        UserWordProgress.view_count.asc(),
        func.random(),
    ).limit(limit)

    rows = (await db.execute(stmt)).all()
    word_ids = [w.id for w, _ in rows]
    forms_progress = await _load_forms_progress(db, user.id, word_ids)
    items = [_word_to_out(w, p, forms_progress) for w, p in rows]
    return WordListOut(items=items, next_cursor=None)


@router.post("/{word_id}/view")
async def mark_viewed(
    word_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Отмечает факт показа карточки пользователю: +1 к view_count, обновляет last_seen_at."""
    exists_stmt = select(Word.id).where(Word.id == word_id)
    found = (await db.execute(exists_stmt)).scalar_one_or_none()
    if not found:
        raise HTTPException(status_code=404, detail="Слово не найдено")
    progress = await mark_word_viewed(db, user.id, word_id)
    return {"view_count": progress.view_count}


@router.get("/dictionary", response_model=WordListOut)
async def list_dictionary(
    category_id: list[int] | None = Query(None),
    difficulty: list[Difficulty] | None = Query(None),
    part_of_speech: list[PartOfSpeech] | None = Query(None),
    status: str | None = Query(
        None, description="learning — в процессе, learned — изученные. Пусто = всё в банке"
    ),
    q: str | None = Query(None, min_length=2, max_length=64, description="Поиск по английскому/русскому"),
    sort: str = Query("recent", pattern="^(recent|alpha|progress)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    cursor: int | None = Query(None, ge=0),
    limit: int = Query(30, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WordListOut:
    """Словарь: все слова в банке пользователя (seen=true), с фильтрами/поиском/сортировкой/пагинацией."""
    stmt = (
        select(Word, UserWordProgress)
        .join(UserWordProgress, UserWordProgress.word_id == Word.id)
        .where(
            UserWordProgress.user_id == user.id,
            UserWordProgress.seen.is_(True),
        )
        .options(selectinload(Word.category), selectinload(Word.forms))
    )
    stmt = _apply_multi_filters(stmt, category_id, difficulty, part_of_speech)

    if status == "learning":
        stmt = stmt.where(UserWordProgress.correct_count < LEARNED_THRESHOLD)
    elif status == "learned":
        stmt = stmt.where(UserWordProgress.correct_count >= LEARNED_THRESHOLD)

    if q:
        pattern = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Word.english).like(pattern),
                func.lower(Word.russian).like(pattern),
            )
        )

    desc = order == "desc"
    if sort == "alpha":
        col = Word.english
        stmt = stmt.order_by(col.desc() if desc else col.asc(), Word.id.asc())
    elif sort == "progress":
        col = UserWordProgress.correct_count
        stmt = stmt.order_by(col.desc() if desc else col.asc(), Word.id.asc())
    else:
        col = UserWordProgress.last_seen_at
        stmt = stmt.order_by(
            col.desc().nulls_last() if desc else col.asc().nulls_last(), Word.id.asc()
        )

    offset = cursor or 0
    stmt = stmt.offset(offset).limit(limit + 1)
    rows = (await db.execute(stmt)).all()

    has_more = len(rows) > limit
    rows = rows[:limit]
    word_ids = [w.id for w, _ in rows]
    forms_progress = await _load_forms_progress(db, user.id, word_ids)
    items = [_word_to_out(w, p, forms_progress) for w, p in rows]
    next_cursor = offset + limit if has_more else None
    return WordListOut(items=items, next_cursor=next_cursor)


@router.get("", response_model=WordListOut)
async def list_words(
    category_id: int | None = Query(None),
    difficulty: Difficulty | None = Query(None),
    part_of_speech: PartOfSpeech | None = Query(None),
    status: str | None = Query(None),
    cursor: int | None = Query(None, description="id последнего элемента предыдущей страницы"),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WordListOut:
    """Legacy-список слов с фильтрами (используется только для обратной совместимости)."""
    stmt = (
        select(Word, UserWordProgress)
        .outerjoin(
            UserWordProgress,
            and_(
                UserWordProgress.word_id == Word.id,
                UserWordProgress.user_id == user.id,
            ),
        )
        .options(selectinload(Word.category), selectinload(Word.forms))
    )

    if category_id is not None:
        stmt = stmt.where(Word.category_id == category_id)
    if difficulty is not None:
        stmt = stmt.where(Word.difficulty == difficulty)
    if part_of_speech is not None:
        stmt = stmt.where(Word.part_of_speech == part_of_speech)

    if status == "new":
        stmt = stmt.where((UserWordProgress.id.is_(None)) | (UserWordProgress.seen.is_(False)))
    elif status == "learning":
        stmt = stmt.where(
            UserWordProgress.seen.is_(True),
            UserWordProgress.correct_count < LEARNED_THRESHOLD,
        )
    elif status == "learned":
        stmt = stmt.where(UserWordProgress.correct_count >= LEARNED_THRESHOLD)

    if cursor is not None:
        stmt = stmt.where(Word.id > cursor)

    stmt = stmt.order_by(Word.id.asc()).limit(limit + 1)
    rows = (await db.execute(stmt)).all()

    has_more = len(rows) > limit
    rows = rows[:limit]
    word_ids = [w.id for w, _ in rows]
    forms_progress = await _load_forms_progress(db, user.id, word_ids)

    items = [_word_to_out(w, p, forms_progress) for w, p in rows]
    next_cursor = items[-1].id if has_more and items else None
    return WordListOut(items=items, next_cursor=next_cursor)


@router.get("/{word_id}", response_model=WordOut)
async def get_word(
    word_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WordOut:
    stmt = (
        select(Word, UserWordProgress)
        .outerjoin(
            UserWordProgress,
            and_(
                UserWordProgress.word_id == Word.id,
                UserWordProgress.user_id == user.id,
            ),
        )
        .options(selectinload(Word.category), selectinload(Word.forms))
        .where(Word.id == word_id)
    )
    row = (await db.execute(stmt)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Слово не найдено")
    word, progress = row
    forms_progress = await _load_forms_progress(db, user.id, [word.id])
    return _word_to_out(word, progress, forms_progress)
