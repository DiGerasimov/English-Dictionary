from typing import Protocol


class TTSEngine(Protocol):
    """Общий интерфейс движков синтеза речи."""

    name: str
    voice: str
    content_type: str

    async def synthesize(self, text: str) -> bytes:
        """Синтезирует речь и возвращает байты аудио в заявленном content_type."""
        ...
