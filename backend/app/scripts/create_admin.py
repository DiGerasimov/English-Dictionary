"""CLI: сделать существующего пользователя администратором по email.

Режимы:
  * ручной:  python -m app.scripts.create_admin user@example.com
             — отсутствие юзера/email завершится ошибкой (код 1/2).
  * авто:    python -m app.scripts.create_admin --auto
             — email берётся из ADMIN_EMAIL; отсутствие юзера/email НЕ считается ошибкой
             (нужно для вызова при старте контейнера).

Примеры:
  make create-admin                              # ручной режим, email из .env
  make create-admin email=user@example.com       # ручной, явный email
  docker compose exec backend python -m app.scripts.create_admin --auto
"""
import asyncio
import os
import sys

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User


async def promote(email: str, *, auto: bool) -> int:
    """Проставляет is_admin=True. В auto-режиме «нет юзера/email» — не ошибка (exit 0)."""
    email = (email or "").strip().lower()
    if not email:
        if auto:
            print("create_admin: ADMIN_EMAIL не задан — пропускаю")
            return 0
        print("ERROR: укажите email (аргументом или в ADMIN_EMAIL)")
        return 2

    async with AsyncSessionLocal() as db:
        user = (
            await db.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if not user:
            if auto:
                print(f"create_admin: пользователь {email!r} ещё не зарегистрирован — пропускаю")
                return 0
            print(f"ERROR: пользователь с email {email!r} не найден")
            return 1
        if user.is_admin:
            print(f"OK: {email} уже является админом")
            return 0
        user.is_admin = True
        await db.commit()
        print(f"OK: {email} теперь администратор")
        return 0


def main() -> None:
    args = [a for a in sys.argv[1:] if a]
    auto = "--auto" in args
    positional = [a for a in args if not a.startswith("--")]
    email = positional[0] if positional else os.getenv("ADMIN_EMAIL", "")
    sys.exit(asyncio.run(promote(email, auto=auto)))


if __name__ == "__main__":
    main()
