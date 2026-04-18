import asyncio
import io
import logging
import urllib.request
import wave
from pathlib import Path

logger = logging.getLogger(__name__)

_HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"


def _voice_hf_path(voice: str) -> str:
    """Парсит идентификатор вида en_US-amy-medium в путь внутри HF-репозитория."""
    try:
        locale, name, quality = voice.split("-", 2)
        lang, _country = locale.split("_", 1)
        return f"{lang}/{locale}/{name}/{quality}/{voice}"
    except ValueError as exc:
        raise ValueError(f"Некорректный идентификатор голоса Piper: {voice}") from exc


def _download_if_missing(url: str, dst: Path) -> None:
    if dst.exists() and dst.stat().st_size > 0:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Piper: загружаю %s", url)
    with urllib.request.urlopen(url) as resp, open(dst, "wb") as fh:
        while True:
            chunk = resp.read(1 << 16)
            if not chunk:
                break
            fh.write(chunk)


class PiperEngine:
    """Синтез речи через Piper (ONNX) — быстрый, лёгкий, CPU-only."""

    name = "piper"
    content_type = "audio/wav"

    def __init__(self, voice: str, models_dir: str) -> None:
        self.voice = voice
        self._models_dir = Path(models_dir) / "piper"
        self._voice_obj = None  # ленивая загрузка
        self._lock = asyncio.Lock()

    async def warmup(self) -> None:
        await self._ensure_loaded()

    async def _ensure_loaded(self):
        if self._voice_obj is not None:
            return self._voice_obj
        async with self._lock:
            if self._voice_obj is not None:
                return self._voice_obj
            self._voice_obj = await asyncio.to_thread(self._load_sync)
            return self._voice_obj

    def _load_sync(self):
        from piper import PiperVoice

        hf_path = _voice_hf_path(self.voice)
        onnx_path = self._models_dir / f"{self.voice}.onnx"
        cfg_path = self._models_dir / f"{self.voice}.onnx.json"
        _download_if_missing(f"{_HF_BASE}/{hf_path}.onnx", onnx_path)
        _download_if_missing(f"{_HF_BASE}/{hf_path}.onnx.json", cfg_path)
        logger.info("Piper: модель %s загружена из %s", self.voice, onnx_path)
        return PiperVoice.load(str(onnx_path), config_path=str(cfg_path))

    async def synthesize(self, text: str) -> bytes:
        voice = await self._ensure_loaded()
        return await asyncio.to_thread(self._synthesize_sync, voice, text)

    @staticmethod
    def _synthesize_sync(voice, text: str) -> bytes:
        """Формирует WAV вручную через synthesize_stream_raw — контролируем заголовок сами."""
        sample_rate = getattr(getattr(voice, "config", None), "sample_rate", 22050)

        raw_chunks: list[bytes] = []
        for audio_bytes in voice.synthesize_stream_raw(text):
            if audio_bytes:
                raw_chunks.append(audio_bytes)

        raw = b"".join(raw_chunks)
        if not raw:
            raise RuntimeError("Piper вернул пустой аудиопоток")

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit PCM
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(raw)

        data = buf.getvalue()
        logger.info(
            "Piper: сгенерирован WAV %d байт (sr=%d, raw=%d) для текста %r",
            len(data),
            sample_rate,
            len(raw),
            text[:50],
        )
        return data
