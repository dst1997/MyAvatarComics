from app.config import Settings
from app.providers.base import AIProvider
from app.providers.mock import MockProvider


def create_provider(settings: Settings) -> AIProvider:
    if settings.use_gemini:
        from app.providers.gemini_provider import GeminiProvider

        return GeminiProvider(settings)
    return MockProvider()
