import asyncio
import io
import logging
import os

logger = logging.getLogger(__name__)


class KokoroEngine:
    """Синтез речи через Kokoro-82M — качество уровня нейро-TTS, заметно тяжелее Piper."""

    name = "kokoro"
    content_type = "audio/wav"

    def __init__(self, voice: str, models_dir: str, lang_code: str = "a") -> None:
        self.voice = voice
        self._lang_code = lang_code
        self._models_dir = models_dir
        self._pipeline = None
        self._lock = asyncio.Lock()

    async def warmup(self) -> None:
        await self._ensure_loaded()

    async def _ensure_loaded(self):
        if self._pipeline is not None:
            return self._pipeline
        async with self._lock:
            if self._pipeline is not None:
                return self._pipeline
            self._pipeline = await asyncio.to_thread(self._load_sync)
            return self._pipeline

    def _load_sync(self):
        # Перенаправляем кэш HF внутрь подмонтированного тома, чтобы веса не скачивались заново
        os.environ.setdefault("HF_HOME", os.path.join(self._models_dir, "kokoro_hf"))
        from kokoro import KPipeline

        logger.info("Kokoro: инициализация пайплайна (%s)", self._lang_code)
        return KPipeline(lang_code=self._lang_code)

    async def synthesize(self, text: str) -> bytes:
        pipeline = await self._ensure_loaded()
        return await asyncio.to_thread(self._synthesize_sync, pipeline, text)

    def _synthesize_sync(self, pipeline, text: str) -> bytes:
        import numpy as np
        import soundfile as sf

        chunks = []
        for _, _, audio in pipeline(text, voice=self.voice):
            if audio is None:
                continue
            arr = audio.detach().cpu().numpy() if hasattr(audio, "detach") else audio
            chunks.append(arr)

        if not chunks:
            raise RuntimeError("Kokoro вернул пустой результат синтеза")

        audio_np = np.concatenate(chunks).astype("float32")
        buf = io.BytesIO()
        sf.write(buf, audio_np, samplerate=24000, format="WAV", subtype="PCM_16")
        return buf.getvalue()
