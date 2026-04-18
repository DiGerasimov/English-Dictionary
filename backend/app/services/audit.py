import logging
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

logger = logging.getLogger("audit")


def _client_ip(request: Request | None) -> str | None:
    """IP клиента с учётом nginx X-Forwarded-For."""
    if request is None:
        return None
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()[:64]
    return request.client.host[:64] if request.client else None


async def log_event(
    db: AsyncSession,
    *,
    action: str,
    user_id: int | None = None,
    request: Request | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    """Пишет событие безопасности в таблицу audit_log + INFO-лог.

    Никогда не кидает исключений наружу — чтобы сбой аудита не ронял основной запрос.
    """
    try:
        ua = None
        if request is not None:
            ua_raw = request.headers.get("user-agent") or ""
            ua = ua_raw[:255] if ua_raw else None
        entry = AuditLog(
            user_id=user_id,
            action=action[:64],
            ip=_client_ip(request),
            user_agent=ua,
            meta=meta,
        )
        db.add(entry)
        await db.commit()
        logger.info("audit action=%s user=%s", action, user_id)
    except Exception as exc:
        logger.warning("Не удалось записать аудит-событие %s: %s", action, exc)
        try:
            await db.rollback()
        except Exception:
            pass
