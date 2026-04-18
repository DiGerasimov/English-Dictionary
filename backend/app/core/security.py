from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Вернёт bcrypt-хеш пароля."""
    return pwd_context.hash(password)


def verify_password(raw: str, hashed: str) -> bool:
    """Проверяет соответствие пароля и хеша."""
    return pwd_context.verify(raw, hashed)


def create_access_token(subject: str | int, expires_minutes: int | None = None) -> str:
    """Создаёт JWT access-token с переданным subject (user id)."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes or settings.jwt_expire_minutes)
    payload: dict[str, Any] = {"sub": str(subject), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any] | None:
    """Декодирует JWT, возвращает payload или None при ошибке."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
