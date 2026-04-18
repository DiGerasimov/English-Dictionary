from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def _client_key(request: Request) -> str:
    """Ключ для лимитов: сначала X-Forwarded-For (nginx), иначе remote_addr."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_client_key, storage_uri="memory://", headers_enabled=False)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Единый ответ при срабатывании лимита: 429 + Retry-After."""
    return JSONResponse(
        status_code=429,
        content={"detail": "Слишком много запросов. Попробуйте позже."},
        headers={"Retry-After": "60"},
    )
