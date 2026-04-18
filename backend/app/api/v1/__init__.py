from fastapi import APIRouter

from app.api.v1 import admin, audio, auth, categories, quiz, stats, words

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(categories.router)
api_router.include_router(words.router)
api_router.include_router(audio.router)
api_router.include_router(quiz.router)
api_router.include_router(stats.router)
api_router.include_router(admin.router)
