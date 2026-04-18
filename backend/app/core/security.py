import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Поддерживаем argon2 (новые пароли) + bcrypt (старые записи), deprecated="auto"
# означает: при успешном логине старый bcrypt-хеш будет перехеширован в argon2.
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Возвращает argon2-хеш пароля."""
    return pwd_context.hash(password)


def verify_password(raw: str, hashed: str) -> bool:
    """Проверяет пароль против хеша (bcrypt или argon2)."""
    try:
        return pwd_context.verify(raw, hashed)
    except Exception:
        return False


def needs_rehash(hashed: str) -> bool:
    """True, если хеш пора обновить (например, был bcrypt, стал argon2)."""
    return pwd_context.needs_update(hashed)


def create_access_token(subject: str | int, expires_minutes: int | None = None) -> str:
    """JWT access-token с jti/iat/exp и subject=user_id."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes or settings.jwt_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": expire,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any] | None:
    """Декодирует JWT, возвращает payload или None при ошибке/истёкшем сроке."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
