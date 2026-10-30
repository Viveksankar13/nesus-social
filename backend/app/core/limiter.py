"""
Rate Limiting Infrastructure
=============================
Configures slowapi rate limiter using client remote IP addresses.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    storage_uri="memory://",
    enabled=settings.ENVIRONMENT != "test",
)
