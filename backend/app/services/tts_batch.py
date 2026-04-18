import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models import Word, WordAudio
from app.services.tts import get_tts_engine

logger = logging.getLogger(__name__)


@dataclass
class BatchState:
    status: str = "idle"  # idle | running | stopping | done | error
    engine: str = ""
    voice: str = ""
    total: int = 0
    processed: int = 0
    errors: int = 0
    current_word: Optional[str] = None
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    last_error: Optional[str] = None
    concurrency: int = 1
    recent: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        elapsed = None
        if self.started_at is not None:
            end = self.finished_at or time.time()
            elapsed = round(end - self.started_at, 1)
        return {
            "status": self.status,
            "engine": self.engine,
            "voice": self.voice,
            "total": self.total,
            "processed": self.processed,
            "errors": self.errors,
            "current_word": self.current_word,
            "elapsed_seconds": elapsed,
            "concurrency": self.concurrency,
            "last_error": self.last_error,
            "recent": list(self.recent[-10:]),
        }


class TTSBatchManager:
    """Одноэкземплярный менеджер фоновой генерации озвучек."""

    def __init__(self) -> None:
        self._state = BatchState()
        self._task: asyncio.Task | None = None
        self._stop_flag = False
        self._lock = asyncio.Lock()

    def status(self) -> dict:
        return self._state.to_dict()

    async def start(self) -> dict:
        async with self._lock:
            if self._task and not self._task.done():
                return self._state.to_dict()
            self._stop_flag = False
            engine = get_tts_engine()
            self._state = BatchState(
                status="running",
                engine=engine.name,
                voice=engine.voice,
                started_at=time.time(),
                concurrency=max(1, int(settings.tts_batch_concurrency)),
            )
            self._task = asyncio.create_task(self._run())
            return self._state.to_dict()

    async def stop(self) -> dict:
        if self._task and not self._task.done():
            self._stop_flag = True
            self._state.status = "stopping"
        return self._state.to_dict()

    async def _run(self) -> None:
        try:
            await self._loop_body()
        except Exception as exc:
            logger.exception("TTS-batch: неожиданная ошибка")
            self._state.status = "error"
            self._state.last_error = str(exc)
        finally:
            self._state.finished_at = time.time()
            if self._state.status == "running":
                self._state.status = "done"
            elif self._state.status == "stopping":
                self._state.status = "idle"

    async def _loop_body(self) -> None:
        engine = get_tts_engine()
        # Прогреваем на всякий случай, чтобы первый батч не стоял
        try:
            await engine.warmup()
        except Exception:
            logger.exception("TTS-batch: не удалось прогреть движок")

        concurrency = max(1, int(settings.tts_batch_concurrency))
        sem = asyncio.Semaphore(concurrency)

        async with AsyncSessionLocal() as count_session:
            self._state.total = await self._count_pending(count_session, engine.name, engine.voice)

        while not self._stop_flag:
            async with AsyncSessionLocal() as session:
                pending = await self._fetch_pending(
                    session, engine.name, engine.voice, limit=concurrency * 4
                )

            if not pending:
                break

            tasks = [
                asyncio.create_task(self._process_one(sem, engine, word_id, english))
                for word_id, english in pending
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

            if self._stop_flag:
                break

    async def _process_one(self, sem: asyncio.Semaphore, engine, word_id: int, english: str) -> None:
        if self._stop_flag:
            return
        async with sem:
            if self._stop_flag:
                return
            self._state.current_word = english
            try:
                audio_bytes = await engine.synthesize(english)
            except Exception as exc:
                self._state.errors += 1
                self._state.last_error = f"{english}: {exc}"
                logger.warning("TTS-batch: ошибка синтеза %s: %s", english, exc)
                return

            if not audio_bytes or len(audio_bytes) < 200:
                self._state.errors += 1
                self._state.last_error = f"{english}: пустой WAV"
                return

            try:
                await self._save(word_id, engine, audio_bytes)
            except Exception as exc:
                self._state.errors += 1
                self._state.last_error = f"{english}: {exc}"
                logger.warning("TTS-batch: ошибка сохранения %s: %s", english, exc)
                return

            self._state.processed += 1
            self._state.recent.append(english)
            if len(self._state.recent) > 50:
                self._state.recent = self._state.recent[-50:]

    @staticmethod
    async def _save(word_id: int, engine, audio_bytes: bytes) -> None:
        """UPSERT через ON CONFLICT, чтобы гонки не падали."""
        async with AsyncSessionLocal() as session:
            stmt = (
                pg_insert(WordAudio)
                .values(
                    word_id=word_id,
                    engine=engine.name,
                    voice=engine.voice,
                    content_type=engine.content_type,
                    audio=audio_bytes,
                )
                .on_conflict_do_nothing(index_elements=["word_id", "engine", "voice"])
            )
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    async def _count_pending(session: AsyncSession, engine_name: str, voice: str) -> int:
        """Считает, сколько слов без озвучки под текущий движок+голос."""
        sub = select(WordAudio.word_id).where(
            WordAudio.engine == engine_name, WordAudio.voice == voice
        )
        stmt = select(func.count()).select_from(Word).where(Word.id.notin_(sub))
        total = await session.execute(stmt)
        return int(total.scalar() or 0)

    @staticmethod
    async def _fetch_pending(
        session: AsyncSession, engine_name: str, voice: str, limit: int
    ) -> list[tuple[int, str]]:
        sub = select(WordAudio.word_id).where(
            WordAudio.engine == engine_name, WordAudio.voice == voice
        )
        stmt = (
            select(Word.id, Word.english)
            .where(Word.id.notin_(sub))
            .order_by(Word.id.asc())
            .limit(limit)
        )
        rows = (await session.execute(stmt)).all()
        return [(r[0], r[1]) for r in rows]


_manager = TTSBatchManager()


def get_batch_manager() -> TTSBatchManager:
    return _manager
