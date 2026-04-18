from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.models import QuizAttempt, UserWordFormProgress, UserWordProgress
from app.models.user import User
from app.schemas.auth import (
    LoginIn,
    PasswordConfirmIn,
    RegisterIn,
    TokenOut,
    UserOut,
    UserSettingsIn,
)
from app.services.activation_service import ensure_active_words
from app.services.audit import log_event

router = APIRouter(prefix="/auth", tags=["auth"])

# Константы антибрутфорса
_MAX_FAILED_LOGINS = 10
_LOCK_MINUTES = 15
_UNIFIED_AUTH_ERROR = "Неверный email или пароль"


def _is_locked(user: User) -> bool:
    return bool(user.locked_until and user.locked_until > datetime.now(timezone.utc))


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,
    data: RegisterIn,
    db: AsyncSession = Depends(get_db),
) -> TokenOut:
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
    await log_event(db, user_id=user.id, action="auth.register", request=request)
    return TokenOut(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenOut)
@limiter.limit("5/minute")
async def login(
    request: Request,
    data: LoginIn,
    db: AsyncSession = Depends(get_db),
) -> TokenOut:
    """Аутентификация по email+паролю. Возвращает единое 401 на любой неуспех."""
    result = await db.execute(select(User).where(User.email == data.email.lower()))
    user = result.scalar_one_or_none()

    if user and _is_locked(user):
        await log_event(
            db,
            user_id=user.id,
            action="auth.login.locked",
            request=request,
            meta={"locked_until": user.locked_until.isoformat() if user.locked_until else None},
        )
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Аккаунт временно заблокирован из-за неудачных попыток входа",
        )

    if not user or not verify_password(data.password, user.password_hash):
        if user:
            user.failed_login_count = (user.failed_login_count or 0) + 1
            if user.failed_login_count >= _MAX_FAILED_LOGINS:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=_LOCK_MINUTES)
                user.failed_login_count = 0
            await db.commit()
            await log_event(
                db,
                user_id=user.id,
                action="auth.login.fail",
                request=request,
                meta={"failed_count": user.failed_login_count},
            )
        else:
            await log_event(
                db,
                user_id=None,
                action="auth.login.fail",
                request=request,
                meta={"email": data.email.lower()},
            )
        raise HTTPException(status_code=401, detail=_UNIFIED_AUTH_ERROR)

    # Успешный логин: сбрасываем счётчик, перехешируем старый bcrypt в argon2
    user.failed_login_count = 0
    user.locked_until = None
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(data.password)
    await db.commit()
    await log_event(db, user_id=user.id, action="auth.login.success", request=request)
    return TokenOut(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
async def me(current: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current)


@router.patch("/me/settings", response_model=UserOut)
async def update_settings(
    request: Request,
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
    await log_event(db, user_id=current.id, action="auth.settings_update", request=request)
    return UserOut.model_validate(current)


@router.post("/me/refill-words")
@limiter.limit("5/minute")
async def refill_words(
    request: Request,
    data: PasswordConfirmIn,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Принудительно открывает новые слова по всем категориям. Требует подтверждение паролем."""
    if not verify_password(data.password, current.password_hash):
        await log_event(db, user_id=current.id, action="auth.refill.deny", request=request)
        raise HTTPException(status_code=401, detail=_UNIFIED_AUTH_ERROR)
    activated = await ensure_active_words(db, current, force_daily=True)
    await log_event(
        db, user_id=current.id, action="auth.refill", request=request, meta={"activated": activated}
    )
    return {"activated": activated}


@router.post("/me/reset-progress")
@limiter.limit("5/minute")
async def reset_progress(
    request: Request,
    data: PasswordConfirmIn,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    """Полностью сбрасывает прогресс пользователя. Требует подтверждение паролем."""
    if not verify_password(data.password, current.password_hash):
        await log_event(db, user_id=current.id, action="auth.reset_progress.deny", request=request)
        raise HTTPException(status_code=401, detail=_UNIFIED_AUTH_ERROR)

    await db.execute(delete(QuizAttempt).where(QuizAttempt.user_id == current.id))
    await db.execute(
        delete(UserWordFormProgress).where(UserWordFormProgress.user_id == current.id)
    )
    await db.execute(
        delete(UserWordProgress).where(UserWordProgress.user_id == current.id)
    )
    await db.commit()
    await log_event(db, user_id=current.id, action="auth.reset_progress", request=request)
    return {"ok": True}
