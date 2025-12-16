import asyncio
import json
from typing import Any, Callable, Optional

from cachetools import TTLCache
from redis.asyncio import Redis

from app.core.config import get_settings


class CacheLayer:
    """
    L1 (process-local TTLCache) + L2 (Redis) cache layer.
    Corrected for async settings loading.
    """

    def __init__(self, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self._settings = None  # Will hold the Settings object once loaded
        self._redis = None  # Will hold the aioredis connection

        # L1 is initialized as None and will be set in init_cache after settings are loaded
        self.l1: Optional[TTLCache] = None

    async def init_cache(self):
        """Initializes settings, L1 cache, and the Redis connection."""
        # Load settings asynchronously (only runs the actual fetch once due to alru_cache)
        if self._settings is None:
            self._settings = await get_settings()

        settings = self._settings  # Alias for convenience

        # 1. Initialize L1 Cache using loaded settings
        if self.l1 is None:
            self.l1 = TTLCache(maxsize=settings.l1_maxsize, ttl=settings.l1_ttl_seconds)

        # 2. Initialize Redis connection
        if self._redis is None:
            self._redis = Redis.from_url(
                settings.redis_dsn, encoding="utf-8", decode_responses=True
            )

    def _l1_key(self, key: str) -> str:
        # Use self._settings
        return f"{self._settings.cache_namespace}l1:{key}"

    def _l2_key(self, key: str) -> str:
        # Use self._settings
        return f"{self._settings.cache_namespace}l2:{key}"

    async def get(
        self,
        key: str,
        loader: Optional[Callable[[], Any]] = None,
        l2_ttl: Optional[int] = None,
    ):
        """
        Try L1 -> L2 -> loader (DB).
        """
        # Ensure all components are initialized before use
        await self.init_cache()

        # Use alias for convenience
        settings = self._settings

        # 1) L1 (sync)
        if key in self.l1:
            return self.l1[key]

        # 2) L2 (redis)
        raw = await self._redis.get(self._l2_key(key))
        if raw is not None:
            # ... (rest of L2 logic is fine)
            try:
                value = json.loads(raw)
            except Exception:
                value = raw
            # update L1
            self.l1[key] = value
            return value

        # 3) loader fallback
        if loader is None:
            return None

        # Stampede Protection Logic (inside lock)
        lock = _get_lock_for_key(key)
        async with lock:
            # Double-check L1 and L2 after acquiring lock
            if key in self.l1:
                return self.l1[key]

            raw = await self._redis.get(self._l2_key(key))
            if raw is not None:
                # ... (L2 logic)
                try:
                    value = json.loads(raw)
                except Exception:
                    value = raw
                self.l1[key] = value
                return value

            # call loader
            value = await loader()
            if value is None:
                return None

            # set L2
            data = json.dumps(value, default=str)
            ttl = l2_ttl or settings.l2_ttl_seconds  # Use settings
            await self._redis.set(self._l2_key(key), data, ex=ttl)
            # set L1
            self.l1[key] = value
            return value

    async def set(self, key: str, value: Any, l2_ttl: Optional[int] = None):
        # Ensure initialization
        await self.init_cache()
        settings = self._settings

        # write-through to both
        self.l1[key] = value
        data = json.dumps(value, default=str)
        ttl = l2_ttl or settings.l2_ttl_seconds  # Use settings
        await self._redis.set(self._l2_key(key), data, ex=ttl)

    async def delete(self, key: str):
        # Ensure initialization
        await self.init_cache()

        self.l1.pop(key, None)
        await self._redis.delete(self._l2_key(key))


# simple per-key lock map (in-memory, per-process) - No change needed here for now
_locks = {}


def _get_lock_for_key(key: str):
    lock = _locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _locks[key] = lock
    return lock


# cache layer instance (singleton per worker)
cache_layer = CacheLayer()
