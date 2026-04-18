import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.models import User, Word, WordAudio
from app.services.tts import get_tts_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/words", tags=["audio"])


@router.get("/{word_id}/audio")
@limiter.limit("30/minute")
async def get_word_audio(
    request: Request,
    word_id: int,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Отдаёт озвучку английского слова, генерируя при первом обращении и кешируя в БД."""
    engine = get_tts_engine()

    cache_stmt = select(WordAudio).where(
        WordAudio.word_id == word_id,
        WordAudio.engine == engine.name,
        WordAudio.voice == engine.voice,
    )
    cached = (await db.execute(cache_stmt)).scalar_one_or_none()
    if cached:
        return Response(
            content=cached.audio,
            media_type=cached.content_type,
            headers={"Cache-Control": "public, max-age=2592000"},
        )

    word = (await db.execute(select(Word).where(Word.id == word_id))).scalar_one_or_none()
    if not word:
        raise HTTPException(status_code=404, detail="Слово не найдено")

    text = (word.english or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="У слова нет текста для озвучивания")

    try:
        audio_bytes = await engine.synthesize(text)
    except Exception as exc:
        logger.exception("TTS: сбой синтеза для word_id=%s", word_id)
        raise HTTPException(status_code=503, detail="Сервис озвучки недоступен") from exc

    if not audio_bytes or len(audio_bytes) < 200:
        logger.error("TTS: подозрительно короткий ответ %d байт для %r", len(audio_bytes), text)
        raise HTTPException(status_code=503, detail="TTS вернул пустое аудио")

    record = WordAudio(
        word_id=word_id,
        engine=engine.name,
        voice=engine.voice,
        content_type=engine.content_type,
        audio=audio_bytes,
    )
    db.add(record)
    try:
        await db.commit()
    except Exception:
        # На гонке UNIQUE-ключ словит конкурентную запись — это норм, отдадим уже имеющуюся
        await db.rollback()
        existing = (await db.execute(cache_stmt)).scalar_one_or_none()
        if existing:
            return Response(
                content=existing.audio,
                media_type=existing.content_type,
                headers={"Cache-Control": "public, max-age=2592000"},
            )
        raise

    return Response(
        content=audio_bytes,
        media_type=engine.content_type,
        headers={"Cache-Control": "public, max-age=2592000"},
    )
