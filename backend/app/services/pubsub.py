"""
Pub/Sub Event Bus Architecture
==============================
Provides an abstract pub/sub interface and an in-memory asyncio implementation.
Designed to be cleanly swappable with Redis for multi-instance deployments.

Architecture:
- BasePubSub: Abstract interface declaring publish() and subscribe().
- InMemoryPubSub: In-process asyncio.Queue based delivery for single-process deployments.
- RedisPubSub (documented): Swappable replacement using redis.asyncio pub/sub.
"""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class BasePubSub(ABC):
    """Abstract interface for real-time pub/sub event distribution."""

    @abstractmethod
    async def publish(self, channel: str, message: dict[str, Any]) -> None:
        """Publish a structured event payload to a named channel."""
        pass

    @abstractmethod
    async def subscribe(
        self,
        channel: str | list[str],
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Subscribe to one or more channels and asynchronously yield incoming events."""
        pass


class InMemoryPubSub(BasePubSub):
    """
    In-process, thread-safe asynchronous Pub/Sub broker using asyncio queues.
    Suitable for development and single-instance production deployments.
    """

    def __init__(self) -> None:
        self._channels: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()

    async def publish(self, channel: str, message: dict[str, Any]) -> None:
        """Deliver a message to all active subscriber queues on the given channel."""
        async with self._lock:
            subscribers = list(self._channels.get(channel, set()))

        if not subscribers:
            return

        for queue in subscribers:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning(
                    "Subscriber queue full; dropping message",
                    extra={"channel": channel},
                )

    async def subscribe(
        self,
        channel: str | list[str],
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Subscribe to one or more channels, returning an async generator yielding messages.
        Guarantees cleanup of queue on subscriber disconnect.
        """
        channels = [channel] if isinstance(channel, str) else list(channel)
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)

        async with self._lock:
            for ch in channels:
                self._channels.setdefault(ch, set()).add(queue)

        try:
            while True:
                message = await queue.get()
                yield message
        finally:
            async with self._lock:
                for ch in channels:
                    if ch in self._channels:
                        self._channels[ch].discard(queue)
                        if not self._channels[ch]:
                            del self._channels[ch]


# ── Global Broker Singleton ──────────────────────────────────────────────────
# In a multi-worker or distributed architecture (e.g. Kubernetes, multiple dynos),
# replace this with a RedisPubSub instance backed by redis.asyncio:
#
# class RedisPubSub(BasePubSub):
#     def __init__(self, redis_url: str):
#         self.redis = redis.asyncio.from_url(redis_url)
#     async def publish(self, channel: str, message: dict[str, Any]) -> None:
#         await self.redis.publish(channel, json.dumps(message))
#     async def subscribe(self, channel: str) -> AsyncGenerator[dict[str, Any], None]:
#         pubsub = self.redis.pubsub()
#         await pubsub.subscribe(channel)
#         async for msg in pubsub.listen():
#             if msg["type"] == "message":
#                 yield json.loads(msg["data"])

pubsub: BasePubSub = InMemoryPubSub()


def get_pubsub() -> BasePubSub:
    """Dependency injector / accessor for pub/sub broker."""
    return pubsub
