from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения, читаются из переменных окружения."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(..., alias="DATABASE_URL")

    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(10080, alias="JWT_EXPIRE_MINUTES")

    cors_origins: str = Field("*", alias="CORS_ORIGINS")

    tts_engine: str = Field("piper", alias="TTS_ENGINE")
    tts_voice_piper: str = Field("en_US-amy-medium", alias="TTS_VOICE_PIPER")
    tts_voice_kokoro: str = Field("af_heart", alias="TTS_VOICE_KOKORO")
    tts_models_dir: str = Field("/app/models/tts", alias="TTS_MODELS_DIR")
    tts_batch_concurrency: int = Field(10, alias="TTS_BATCH_CONCURRENCY")

    @property
    def cors_origins_list(self) -> list[str]:
        """Список доверенных origin'ов. При пустом значении приложение падает на старте."""
        raw = (self.cors_origins or "").strip()
        if not raw or raw == "*":
            raise RuntimeError(
                "CORS_ORIGINS не задан или равен '*'. "
                "Укажите явные домены, например http://localhost:8080"
            )
        return [o.strip() for o in raw.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
