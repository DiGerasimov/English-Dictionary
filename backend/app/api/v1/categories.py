from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Category, User, UserPinnedCategory, UserWordProgress, Word
from app.models.progress import LEARNED_THRESHOLD
from app.schemas.category import CategoryOut

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
async def list_categories(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CategoryOut]:
    """Список категорий с агрегированным прогрессом пользователя и флагом закрепления."""
    words_cnt_q = (
        select(Word.category_id, func.count(Word.id).label("cnt"))
        .group_by(Word.category_id)
        .subquery()
    )

    seen_cnt = func.count(UserWordProgress.id).label("seen_cnt")
    learned_cnt = func.sum(
        case((UserWordProgress.correct_count >= LEARNED_THRESHOLD, 1), else_=0)
    ).label("learned_cnt")
    ready_cnt = func.sum(
        case((UserWordProgress.correct_count < LEARNED_THRESHOLD, 1), else_=0)
    ).label("ready_cnt")

    seen_sub = (
        select(
            Word.category_id.label("cid"),
            seen_cnt,
            learned_cnt,
            ready_cnt,
        )
        .join(UserWordProgress, UserWordProgress.word_id == Word.id)
        .where(UserWordProgress.user_id == user.id, UserWordProgress.seen.is_(True))
        .group_by(Word.category_id)
        .subquery()
    )

    pinned_stmt = select(UserPinnedCategory.category_id).where(
        UserPinnedCategory.user_id == user.id
    )
    pinned_ids = {row[0] for row in (await db.execute(pinned_stmt)).all()}

    stmt = (
        select(
            Category,
            func.coalesce(words_cnt_q.c.cnt, 0),
            func.coalesce(seen_sub.c.seen_cnt, 0),
            func.coalesce(seen_sub.c.learned_cnt, 0),
            func.coalesce(seen_sub.c.ready_cnt, 0),
        )
        .outerjoin(words_cnt_q, words_cnt_q.c.category_id == Category.id)
        .outerjoin(seen_sub, seen_sub.c.cid == Category.id)
        .order_by(Category.order_index.asc(), Category.id.asc())
    )
    rows = (await db.execute(stmt)).all()

    result: list[CategoryOut] = []
    for c, words_count, seen_count, learned_count, ready_count in rows:
        total = int(words_count or 0)
        seen = int(seen_count or 0)
        result.append(
            CategoryOut(
                id=c.id,
                slug=c.slug,
                name_ru=c.name_ru,
                name_en=c.name_en,
                icon=c.icon,
                description=c.description,
                order_index=c.order_index,
                words_count=total,
                seen_count=seen,
                learned_count=int(learned_count or 0),
                quiz_ready_count=int(ready_count or 0),
                new_available_count=max(0, total - seen),
                is_pinned=c.id in pinned_ids,
            )
        )
    return result


@router.post("/{category_id}/pin", status_code=status.HTTP_204_NO_CONTENT)
async def pin_category(
    category_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Закрепляет категорию у пользователя (idempotent)."""
    cat = await db.get(Category, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Категория не найдена")

    existing = await db.execute(
        select(UserPinnedCategory).where(
            UserPinnedCategory.user_id == user.id,
            UserPinnedCategory.category_id == category_id,
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(UserPinnedCategory(user_id=user.id, category_id=category_id))
        await db.commit()


@router.delete("/{category_id}/pin", status_code=status.HTTP_204_NO_CONTENT)
async def unpin_category(
    category_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Снимает закрепление категории у пользователя."""
    await db.execute(
        delete(UserPinnedCategory).where(
            UserPinnedCategory.user_id == user.id,
            UserPinnedCategory.category_id == category_id,
        )
    )
    await db.commit()
