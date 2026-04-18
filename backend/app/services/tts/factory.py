import logging
from functools import lru_cache

from app.core.config import settings
from app.services.tts.base import TTSEngine

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_tts_engine() -> TTSEngine:
    """Возвращает singleton-движка согласно TTS_ENGINE. Импорт реализаций — ленивый."""
    engine_name = (settings.tts_engine or "piper").lower().strip()

    if engine_name == "piper":
        from app.services.tts.piper_engine import PiperEngine

        logger.info("TTS: выбран движок Piper (voice=%s)", settings.tts_voice_piper)
        return PiperEngine(voice=settings.tts_voice_piper, models_dir=settings.tts_models_dir)

    if engine_name == "kokoro":
        from app.services.tts.kokoro_engine import KokoroEngine

        logger.info("TTS: выбран движок Kokoro (voice=%s)", settings.tts_voice_kokoro)
        return KokoroEngine(voice=settings.tts_voice_kokoro, models_dir=settings.tts_models_dir)

    raise ValueError(f"Неизвестный TTS_ENGINE: {engine_name!r}. Ожидается 'piper' или 'kokoro'")
