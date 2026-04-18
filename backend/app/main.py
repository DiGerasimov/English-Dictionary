import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.services.tts import get_tts_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Прогревает TTS-движок при старте, чтобы первый запрос не был долгим."""
    try:
        engine = get_tts_engine()
        await engine.warmup()
        logger.info("TTS-движок %s готов", engine.name)
    except Exception as exc:
        logger.warning("Не удалось прогреть TTS-движок: %s", exc)
    yield


def create_app() -> FastAPI:
    """Создаёт FastAPI приложение со всеми роутерами и middleware."""
    app = FastAPI(title="English Learning App", version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
