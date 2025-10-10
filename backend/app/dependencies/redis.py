"""FastAPI dependency for Redis connections."""

from __future__ import annotations

from typing import Optional

from redis.asyncio import Redis

from ..config import settings
from ..utils.redis import get_redis_client


async def get_redis() -> Optional[Redis]:
    """Return a Redis client instance or ``None`` when unavailable."""

    return await get_redis_client(settings.REDIS_URL)
