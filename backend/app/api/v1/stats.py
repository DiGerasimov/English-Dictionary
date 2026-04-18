from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Category, QuizAttempt, User, UserWordProgress, Word
from app.models.progress import LEARNED_THRESHOLD
from app.schemas.stats import (
    ByCategoryOut,
    CategoryStatOut,
    OverviewOut,
    TimelineOut,
    TimelinePoint,
)

router = APIRouter(prefix="/stats", tags=["stats"])


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


@router.get("/overview", response_model=OverviewOut)
async def overview(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OverviewOut:
    """Сводные показатели пользователя — карточки на экране статистики."""
    today = _today_utc()
    yesterday = today - timedelta(days=1)

    learned_total_stmt = select(func.count(UserWordProgress.id)).where(
        UserWordProgress.user_id == user.id,
        UserWordProgress.correct_count >= LEARNED_THRESHOLD,
    )
    learned_total = (await db.execute(learned_total_stmt)).scalar_one() or 0

    seen_total_stmt = select(func.count(UserWordProgress.id)).where(
        UserWordProgress.user_id == user.id, UserWordProgress.seen.is_(True)
    )
    seen_total = (await db.execute(seen_total_stmt)).scalar_one() or 0

    learned_today_stmt = select(func.count(UserWordProgress.id)).where(
        UserWordProgress.user_id == user.id,
        UserWordProgress.learned_at.is_not(None),
        func.date(UserWordProgress.learned_at) == today,
    )
    learned_today = (await db.execute(learned_today_stmt)).scalar_one() or 0

    learned_yesterday_stmt = select(func.count(UserWordProgress.id)).where(
        UserWordProgress.user_id == user.id,
        UserWordProgress.learned_at.is_not(None),
        func.date(UserWordProgress.learned_at) == yesterday,
    )
    learned_yesterday = (await db.execute(learned_yesterday_stmt)).scalar_one() or 0

    today_counts_stmt = select(
        func.sum(case((QuizAttempt.is_correct.is_(True), 1), else_=0)),
        func.sum(case((QuizAttempt.is_correct.is_(False), 1), else_=0)),
    ).where(QuizAttempt.user_id == user.id, func.date(QuizAttempt.created_at) == today)
    correct_today, incorrect_today = (await db.execute(today_counts_stmt)).one()

    total_counts_stmt = select(
        func.sum(case((QuizAttempt.is_correct.is_(True), 1), else_=0)),
        func.count(QuizAttempt.id),
    ).where(QuizAttempt.user_id == user.id)
    total_correct, total_attempts = (await db.execute(total_counts_stmt)).one()
    accuracy_total = (total_correct or 0) / total_attempts if total_attempts else 0.0

    streak = await _compute_streak(db, user.id, today)

    return OverviewOut(
        learned_today=int(learned_today),
        learned_yesterday=int(learned_yesterday),
        learned_total=int(learned_total),
        seen_total=int(seen_total),
        correct_today=int(correct_today or 0),
        incorrect_today=int(incorrect_today or 0),
        accuracy_total=round(accuracy_total, 4),
        streak_days=streak,
    )


async def _compute_streak(db: AsyncSession, user_id: int, today: date) -> int:
    """Считает серию дней подряд с хотя бы одной попыткой."""
    stmt = (
        select(func.date(QuizAttempt.created_at).label("d"))
        .where(QuizAttempt.user_id == user_id)
        .group_by("d")
        .order_by("d")
    )
    days = {row[0] for row in (await db.execute(stmt)).all()}
    streak = 0
    cur = today
    while cur in days:
        streak += 1
        cur -= timedelta(days=1)
    return streak


@router.get("/timeline", response_model=TimelineOut)
async def timeline(
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TimelineOut:
    """Данные по дням для линейного графика (правильные/неправильные/изученные)."""
    today = _today_utc()
    start = today - timedelta(days=days - 1)

    attempts_stmt = (
        select(
            func.date(QuizAttempt.created_at).label("d"),
            func.sum(case((QuizAttempt.is_correct.is_(True), 1), else_=0)),
            func.sum(case((QuizAttempt.is_correct.is_(False), 1), else_=0)),
        )
        .where(QuizAttempt.user_id == user.id, func.date(QuizAttempt.created_at) >= start)
        .group_by("d")
    )
    attempts_map: dict[date, tuple[int, int]] = {}
    for d, c, ic in (await db.execute(attempts_stmt)).all():
        attempts_map[d] = (int(c or 0), int(ic or 0))

    learned_stmt = (
        select(
            func.date(UserWordProgress.learned_at).label("d"),
            func.count(UserWordProgress.id),
        )
        .where(
            UserWordProgress.user_id == user.id,
            UserWordProgress.learned_at.is_not(None),
            func.date(UserWordProgress.learned_at) >= start,
        )
        .group_by("d")
    )
    learned_map: dict[date, int] = {d: int(cnt or 0) for d, cnt in (await db.execute(learned_stmt)).all()}

    points: list[TimelinePoint] = []
    for i in range(days):
        d = start + timedelta(days=i)
        correct, incorrect = attempts_map.get(d, (0, 0))
        points.append(
            TimelinePoint(date=d, correct=correct, incorrect=incorrect, learned=learned_map.get(d, 0))
        )
    return TimelineOut(points=points)


@router.get("/by-category", response_model=ByCategoryOut)
async def by_category(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ByCategoryOut:
    """Разбивка прогресса по категориям для карточек/диаграмм."""
    words_cnt_sub = (
        select(Word.category_id, func.count(Word.id).label("cnt")).group_by(Word.category_id).subquery()
    )

    progress_sub = (
        select(
            Word.category_id.label("cid"),
            func.count(UserWordProgress.id).label("seen"),
            func.sum(case((UserWordProgress.correct_count >= LEARNED_THRESHOLD, 1), else_=0)).label(
                "learned"
            ),
        )
        .join(UserWordProgress, UserWordProgress.word_id == Word.id)
        .where(UserWordProgress.user_id == user.id, UserWordProgress.seen.is_(True))
        .group_by(Word.category_id)
        .subquery()
    )

    attempts_sub = (
        select(
            QuizAttempt.category_id.label("cid"),
            func.sum(case((QuizAttempt.is_correct.is_(True), 1), else_=0)).label("correct"),
            func.sum(case((QuizAttempt.is_correct.is_(False), 1), else_=0)).label("incorrect"),
        )
        .where(QuizAttempt.user_id == user.id, QuizAttempt.category_id.is_not(None))
        .group_by(QuizAttempt.category_id)
        .subquery()
    )

    stmt = (
        select(
            Category,
            func.coalesce(words_cnt_sub.c.cnt, 0),
            func.coalesce(progress_sub.c.seen, 0),
            func.coalesce(progress_sub.c.learned, 0),
            func.coalesce(attempts_sub.c.correct, 0),
            func.coalesce(attempts_sub.c.incorrect, 0),
        )
        .outerjoin(words_cnt_sub, words_cnt_sub.c.category_id == Category.id)
        .outerjoin(progress_sub, progress_sub.c.cid == Category.id)
        .outerjoin(attempts_sub, attempts_sub.c.cid == Category.id)
        .order_by(Category.order_index.asc(), Category.id.asc())
    )
    rows = (await db.execute(stmt)).all()

    items: list[CategoryStatOut] = []
    for cat, wc, seen, learned, correct, incorrect in rows:
        total_attempts = int(correct or 0) + int(incorrect or 0)
        accuracy = (int(correct or 0) / total_attempts) if total_attempts else 0.0
        items.append(
            CategoryStatOut(
                category_id=cat.id,
                slug=cat.slug,
                name_ru=cat.name_ru,
                icon=cat.icon,
                words_count=int(wc or 0),
                seen_count=int(seen or 0),
                learned_count=int(learned or 0),
                correct=int(correct or 0),
                incorrect=int(incorrect or 0),
                accuracy=round(accuracy, 4),
            )
        )
    return ByCategoryOut(items=items)
