"""
AI Service Factory
==================
Exports the active AI service implementation and dependency injection helper.
"""

from functools import lru_cache

from app.core.config import settings
from app.services.ai.base import BaseAIService
from app.services.ai.gemini_service import GeminiAIService
from app.services.ai.mock_service import MockAIService


@lru_cache
def get_ai_service() -> BaseAIService:
    """
    Dependency provider for AI service.
    Returns MockAIService during tests or when GEMINI_API_KEY is not configured.
    Returns GeminiAIService in production and development when key is present.
    """
    key = settings.GEMINI_API_KEY
    if (
        settings.ENVIRONMENT == "test"
        or not key
        or key.startswith("dummy_")
        or key.startswith("CHANGE_ME")
    ):
        return MockAIService()

    return GeminiAIService(api_key=key, model=settings.GEMINI_MODEL)


__all__ = ["BaseAIService", "GeminiAIService", "MockAIService", "get_ai_service"]
