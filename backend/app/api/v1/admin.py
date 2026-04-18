from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_admin_user
from app.models import User
from app.services.audit import log_event
from app.services.tts_batch import get_batch_manager

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/tts/batch")
async def tts_batch_status(_admin: User = Depends(get_admin_user)) -> dict:
    """Текущий статус фоновой генерации озвучек."""
    return get_batch_manager().status()


@router.post("/tts/batch/start")
async def tts_batch_start(
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Запускает генерацию недостающих озвучек (idempotent — повторный вызов игнорируется)."""
    result = await get_batch_manager().start()
    await log_event(db, user_id=admin.id, action="admin.tts_batch_start", request=request)
    return result


@router.post("/tts/batch/stop")
async def tts_batch_stop(
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Останавливает фоновую задачу после завершения текущего батча."""
    result = await get_batch_manager().stop()
    await log_event(db, user_id=admin.id, action="admin.tts_batch_stop", request=request)
    return result
