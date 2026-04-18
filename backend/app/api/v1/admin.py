from fastapi import APIRouter, Depends

from app.core.deps import get_admin_user
from app.models import User
from app.services.tts_batch import get_batch_manager

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/tts/batch")
async def tts_batch_status(_admin: User = Depends(get_admin_user)) -> dict:
    """Текущий статус фоновой генерации озвучек."""
    return get_batch_manager().status()


@router.post("/tts/batch/start")
async def tts_batch_start(_admin: User = Depends(get_admin_user)) -> dict:
    """Запускает генерацию недостающих озвучек (idempotent — повторный вызов игнорируется)."""
    return await get_batch_manager().start()


@router.post("/tts/batch/stop")
async def tts_batch_stop(_admin: User = Depends(get_admin_user)) -> dict:
    """Останавливает фоновую задачу после завершения текущего батча."""
    return await get_batch_manager().stop()
