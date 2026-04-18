from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models import QuizAttempt, UserWordFormProgress, UserWordProgress
from app.models.user import User
from app.schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut, UserSettingsIn
from app.services.activation_service import ensure_active_words

router = APIRouter(prefix="/auth", tags=["auth"])


async def _promote_admin_if_needed(db: AsyncSession, user: User) -> None:
    """Если email совпадает с ADMIN_EMAIL — один раз повышает пользователя до админа."""
    admin_email = (settings.admin_email or "").strip().lower()
    if admin_email and user.email == admin_email and not user.is_admin:
        user.is_admin = True
        await db.commit()


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterIn, db: AsyncSession = Depends(get_db)) -> TokenOut:
    """Создаёт нового пользователя и сразу возвращает JWT."""
    existing = await db.execute(select(User).where(User.email == data.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Пользователь с таким email уже существует")

    user = User(
        email=data.email.lower(),
        username=data.username,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await _promote_admin_if_needed(db, user)
    return TokenOut(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, db: AsyncSession = Depends(get_db)) -> TokenOut:
    """Аутентификация по email+паролю, возвращает JWT."""
    result = await db.execute(select(User).where(User.email == data.email.lower()))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    await _promote_admin_if_needed(db, user)
    return TokenOut(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
async def me(current: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current)


@router.patch("/me/settings", response_model=UserOut)
async def update_settings(
    data: UserSettingsIn,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """Обновляет настройки обучения пользователя."""
    current.active_slots = data.active_slots
    current.daily_new_limit = data.daily_new_limit
    current.voice_mode = data.voice_mode
    await db.commit()
    await db.refresh(current)
    return UserOut.model_validate(current)


@router.post("/me/refill-words")
async def refill_words(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Принудительно открывает новые слова по всем категориям, игнорируя дневной лимит.

    Ведёт себя как наступление нового дня: заполняет активные слоты в каждой категории.
    """
    activated = await ensure_active_words(db, current, force_daily=True)
    return {"activated": activated}


@router.post("/me/reset-progress")
async def reset_progress(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    """Полностью сбрасывает прогресс пользователя: слова, формы и историю квизов."""
    await db.execute(delete(QuizAttempt).where(QuizAttempt.user_id == current.id))
    await db.execute(
        delete(UserWordFormProgress).where(UserWordFormProgress.user_id == current.id)
    )
    await db.execute(
        delete(UserWordProgress).where(UserWordProgress.user_id == current.id)
    )
    await db.commit()
    return {"ok": True}
