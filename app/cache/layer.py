import asyncio
import json
from typing import Any, Callable, Optional

from cachetools import TTLCache
from redis.asyncio import Redis

from app.core.config import get_settings


class RedisMemoryGuard:
    def __init__(self, redis: Redis, refresh_interval: int = 5):
        self.redis = redis
        self.refresh_interval = refresh_interval
        self._last_check = 0
        self._cached = None

    async def check(self) -> dict:
        now = asyncio.get_event_loop().time()
        if self._cached and (now - self._last_check) < self.refresh_interval:
            return self._cached

        info = await self.redis.info("memory")
        used = info["used_memory"]
        maxm = info.get("maxmemory", 0)

        if maxm == 0:
            result = {
                "level": 0,
                "ratio": None,
                "policy": info.get("maxmemory_policy"),
            }
        else:
            ratio = used / maxm
            result = {
                "level": int(min(ratio * 10, 10)),
                "ratio": ratio,
                "policy": info.get("maxmemory_policy"),
            }

        self._cached = result
        self._last_check = now
        return result


class CacheLayer:
    """
    L1 (process-local TTLCache) + L2 (Redis) cache layer.
    Corrected for async settings loading.
    """

    def __init__(self, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self._settings = None  # Will hold the Settings object once loaded
        self._redis = None  # Will hold the aioredis connection
        self._memory_guard = None  # Will handle backpressure

        # L1 is initialized as None and will be set in init_cache after settings are loaded
        self.l1: Optional[TTLCache] = None

    async def init_cache(self):
        """Initializes settings, L1 cache, and the Redis connection."""
        # Load settings asynchronously (only runs the actual fetch once due to alru_cache)
        if self._settings is None:
            self._settings = get_settings()

        settings = self._settings  # Alias for convenience

        # 1. Initialize L1 Cache using loaded settings
        if self.l1 is None:
            self.l1 = TTLCache(maxsize=settings.l1_maxsize, ttl=settings.l1_ttl_seconds)

        # 2. Initialize Redis connection
        if self._redis is None:
            self._redis = Redis.from_url(
                settings.redis_dsn, encoding="utf-8", decode_responses=True
            )

        if self._memory_guard is None:
            self._memory_guard = RedisMemoryGuard(self._redis)

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

        pressure = await self._memory_guard.check()
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

            if pressure["level"] >= 10:
                return await loader() if loader else None

            # call loader
            value = await loader()
            if value is None:
                return None

            # set L2
           

            ttl = l2_ttl or settings.l2_ttl_seconds  # Use settings

            pressure = await self._memory_guard.check()
            pressure_level = pressure["level"]
            if pressure["level"] >= 9:
                self.l1[key] = value
                return value

            if pressure_level >= 7:
                ttl = min(ttl, 60)
            elif pressure_level >= 5:
                ttl = int(ttl * 0.8)
                ttl = max(ttl, 1)
            
            data = json.dumps(value, default=str)

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

        pressure = await self._memory_guard.check()
        if pressure["level"] >= 9:
            return  # skip Redis write

        data = json.dumps(value, default=str)
        ttl = l2_ttl or settings.l2_ttl_seconds  # Use settings

        if pressure["level"] >= 7:
            ttl = min(ttl, 60)
        elif pressure["level"] >= 5:
            ttl = int(ttl * 0.8)
            ttl = max(ttl, 1)

        await self._redis.set(self._l2_key(key), data, ex=ttl)

    async def delete(self, key: str):
        # Ensure initialization
        await self.init_cache()

        pressure = await self._memory_guard.check()
        if pressure["level"] >= 10:
            self.l1.pop(key, None)
            return

        self.l1.pop(key, None)
        await self._redis.delete(self._l2_key(key))


# Lock management for cache stampede protection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# When multiple concurrent requests try to load the same cache key,
# we use per-key locks to ensure only ONE request hits the database
# while others wait for the result (thundering herd prevention).
#
# Implementation details:
# • TTLCache provides bounded memory with automatic eviction (maxsize=10k locks)
# • TTL of 300s (5 min) exceeds worst-case DB operation time to prevent
#   locks from expiring while operations are in progress
# • setdefault() ensures atomic lock creation - all concurrent callers
#   for the same key get the SAME lock object (no race condition)
# • Locks are automatically cleaned up 300s after last access
#
# Memory overhead: ~10KB for full cache (10k locks × ~1KB each)
_locks = TTLCache(maxsize=10_000, ttl=300)


def _get_lock_for_key(key: str) -> asyncio.Lock:
    """
    Get or create an asyncio.Lock for a cache key.

    Uses atomic setdefault() to prevent race conditions where multiple
    concurrent requests could create different lock objects for the same key.

    Args:
        key: Cache key to get lock for

    Returns:
        asyncio.Lock: Shared lock instance for this key
    """
    return _locks.setdefault(key, asyncio.Lock())


# cache layer instance (singleton per worker)
cache_layer = CacheLayer()
