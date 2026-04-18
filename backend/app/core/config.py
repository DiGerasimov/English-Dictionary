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

    admin_email: str = Field("", alias="ADMIN_EMAIL")

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins.strip() in {"", "*"}:
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
