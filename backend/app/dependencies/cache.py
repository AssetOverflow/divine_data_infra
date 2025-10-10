"""FastAPI dependency injection helpers for cache utilities."""

from __future__ import annotations

from functools import lru_cache

from ..config import settings
from ..utils.cache import CacheManager


@lru_cache(maxsize=1)
def get_cache_manager() -> CacheManager:
    """Return a singleton CacheManager configured from settings."""

    return CacheManager(
        redis_url=settings.REDIS_URL,
        default_ttl=settings.CACHE_TTL_SECONDS,
        max_items=settings.CACHE_MAX_ITEMS,
        namespace=settings.CACHE_NAMESPACE,
    )


cache_manager = get_cache_manager
