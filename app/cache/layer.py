import asyncio
import json
from typing import Any, Callable, Optional

from cachetools import TTLCache
from redis.asyncio import Redis, RedisError

from app.core.config import get_settings

import logging

logger = logging.getLogger(__name__)


class RedisMemoryGuard:
    """
    Monitors Redis memory usage and provides backpressure signals.

    Pressure levels:
    - 0-4: Normal operation
    - 5-6: Moderate pressure (reduce TTL by 20%)
    - 7-8: High pressure (cap TTL at 60s)
    - 9: Critical (skip Redis writes, L1 only)
    - 10: Emergency (skip all caching, direct DB)
    """

    def __init__(self, redis: Redis, refresh_interval: int = 5):
        self.redis = redis
        self.refresh_interval = refresh_interval
        self._last_check = 0
        self._cached = None

    async def check(self) -> dict:
        print("Checking for backpressure...")
        """Check memory pressure with caching to avoid INFO spam."""
        now = asyncio.get_event_loop().time()

        # Return cached result if within refresh interval
        if self._cached and (now - self._last_check) < self.refresh_interval:
            return self._cached

        try:
            info = await self.redis.info("memory")
            used = info["used_memory"]
            maxm = info.get("maxmemory", 0)

            if maxm == 0:
                # No memory limit configured
                result = {
                    "level": 0,
                    "ratio": None,
                    "policy": info.get("maxmemory_policy", "noeviction"),
                    "used_mb": used / (1024 * 1024),
                }
            else:
                ratio = used / maxm
                result = {
                    "level": int(min(ratio * 10, 10)),
                    "ratio": ratio,
                    "policy": info.get("maxmemory_policy", "noeviction"),
                    "used_mb": used / (1024 * 1024),
                    "max_mb": maxm / (1024 * 1024),
                }

                # Log warnings at high pressure
                if result["level"] >= 9:
                    logger.warning(
                        "Redis memory critical",
                        level=result["level"],
                        ratio=f"{ratio:.1%}",
                        policy=result["policy"],
                    )
                elif result["level"] >= 7:
                    logger.info(
                        "Redis memory high", level=result["level"], ratio=f"{ratio:.1%}"
                    )

            self._cached = result
            self._last_check = now
            return result

        except RedisError as e:
            logger.error(f"Memory check failed: {e}")
            # Return safe default on error
            return {"level": 0, "ratio": None, "policy": "unknown", "error": str(e)}


class CacheLayer:
    """
    Two-tier cache with adaptive backpressure.

    L1: Process-local TTLCache (fast, limited size)
    L2: Redis (shared, larger capacity)

    Features:
    - Stampede protection with per-key locks
    - Adaptive TTL based on Redis memory pressure
    - Graceful degradation when Redis is unavailable
    - Automatic key namespacing
    """

    def __init__(self, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self._settings = None
        self._redis: Redis | None = None
        self._memory_guard: RedisMemoryGuard | None = None
        self.l1: TTLCache | None = None
        self._initialized = False

        # Stats tracking
        self.stats = {
            "l1_hits": 0,
            "l2_hits": 0,
            "misses": 0,
            "errors": 0,
            "pressure_skips": 0,
        }

    async def init_cache(self):
        """Initialize settings, L1 cache, and Redis connection."""
        if self._initialized:
            return

        try:
            if self._settings is None:
                self._settings = get_settings()

            settings = self._settings

            # Initialize L1 Cache
            if self.l1 is None:
                self.l1 = TTLCache(
                    maxsize=settings.l1_maxsize, ttl=settings.l1_ttl_seconds
                )

            # Initialize Redis connection with proper config
            if self._redis is None:
                self._redis = Redis.from_url(
                    settings.redis_dsn,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=settings.redis_pool_size,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                    health_check_interval=30,
                )

                # Verify connection
                await self._redis.ping()
                logger.info("Redis connection established")

            # Initialize memory guard
            if self._memory_guard is None:
                self._memory_guard = RedisMemoryGuard(self._redis)

            self._initialized = True
            logger.info("Cache layer initialized")

        except RedisError as e:
            logger.error(f"Redis initialization failed: {e}")
            # Allow degraded operation (L1 only)
            self._redis = None
            self._memory_guard = None
        except Exception as e:
            logger.error(f"Cache initialization failed: {e}")
            raise

    def _l1_key(self, key: str) -> str:
        """Build namespaced L1 cache key."""
        return f"{self._settings.cache_namespace}l1:{key}"

    def _l2_key(self, key: str) -> str:
        """Build namespaced L2 cache key."""
        return f"{self._settings.cache_namespace}l2:{key}"

    def _serialize(self, value: Any) -> str:
        """Serialize value for storage."""
        try:
            return json.dumps(value, default=str)
        except (TypeError, ValueError) as e:
            logger.error(f"Serialization failed: {e}")
            raise

    def _deserialize(self, raw: str) -> Any:
        """Deserialize value from storage."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Return raw string if not valid JSON
            return raw

    async def _adjust_ttl_for_pressure(self, base_ttl: int) -> int:
        """Adjust TTL based on current memory pressure."""
        if not self._memory_guard:
            return base_ttl

        pressure = await self._memory_guard.check()
        level = pressure["level"]

        if level >= 9:
            # Critical: Skip Redis entirely
            return 0
        elif level >= 7:
            # High pressure: Cap at 60s
            return min(base_ttl, 60)
        elif level >= 5:
            # Moderate pressure: Reduce by 20%
            return max(int(base_ttl * 0.8), 1)
        else:
            # Normal operation
            return base_ttl

    async def get(
        self,
        key: str,
        loader: Optional[Callable[[], Any]] = None,
        l2_ttl: Optional[int] = None,
    ):
        """
        Retrieve value from cache hierarchy: L1 -> L2 -> loader.

        Args:
            key: Cache key (will be namespaced automatically)
            loader: Async function to load value on cache miss
            l2_ttl: TTL for L2 cache in seconds (uses default if None)

        Returns:
            Cached value or loaded value, or None if not found
        """
        await self.init_cache()

        l1_key = self._l1_key(key)
        l2_key = self._l2_key(key)

        # 1) Check L1 (fast path)
        if l1_key in self.l1:
            self.stats["l1_hits"] += 1
            logger.debug("L1 hit", key=key)
            return self.l1[l1_key]

        # 2) Check L2 (Redis)
        if self._redis:
            try:
                raw = await self._redis.get(l2_key)
                if raw is not None:
                    self.stats["l2_hits"] += 1
                    logger.debug("L2 hit", key=key)
                    value = self._deserialize(raw)
                    # Populate L1
                    self.l1[l1_key] = value
                    return value
            except RedisError as e:
                logger.error(f"Redis GET error: {e}", key=key)
                self.stats["errors"] += 1

        # 3) Load from source (with stampede protection)
        if loader is None:
            self.stats["misses"] += 1
            logger.debug("Cache miss, no loader", key=key)
            return None

        # Check if memory is critical BEFORE acquiring lock
        if self._memory_guard:
            pressure = await self._memory_guard.check()
            if pressure["level"] >= 10:
                # Emergency: Skip all caching, go direct to DB
                logger.warning("Emergency mode: direct DB access", key=key)
                self.stats["pressure_skips"] += 1
                return await loader()

        # Acquire per-key lock for stampede protection
        lock = _get_lock_for_key(key)
        async with lock:
            # Double-check caches after acquiring lock
            if l1_key in self.l1:
                return self.l1[l1_key]

            if self._redis:
                try:
                    raw = await self._redis.get(l2_key)
                    if raw is not None:
                        value = self._deserialize(raw)
                        self.l1[l1_key] = value
                        return value
                except RedisError as e:
                    logger.error(f"Redis double-check error: {e}", key=key)

            # Load value
            self.stats["misses"] += 1
            logger.debug("Loading from source", key=key)
            value = await loader()

            if value is None:
                return None

            # Store in caches with adaptive TTL
            await self._set_both_layers(key, value, l2_ttl)
            return value

    async def _set_both_layers(self, key: str, value: Any, l2_ttl: int | None = None):
        """Internal method to set both cache layers with pressure handling."""
        l1_key = self._l1_key(key)
        l2_key = self._l2_key(key)

        # Always set L1 (it's local and fast)
        self.l1[l1_key] = value

        # Set L2 with adaptive TTL based on pressure
        if self._redis:
            try:
                base_ttl = l2_ttl or self._settings.l2_ttl_seconds
                ttl = await self._adjust_ttl_for_pressure(base_ttl)

                if ttl == 0:
                    # Critical pressure: Skip Redis write
                    logger.debug("Skipping Redis write due to pressure", key=key)
                    self.stats["pressure_skips"] += 1
                    return

                data = self._serialize(value)
                await self._redis.set(l2_key, data, ex=ttl)
                logger.debug("Stored in L2", key=key, ttl=ttl)

            except RedisError as e:
                logger.error(f"Redis SET error: {e}", key=key)
                self.stats["errors"] += 1

    async def set(self, key: str, value: Any, l2_ttl: Optional[int] = None):
        """
        Explicitly set a value in both cache layers.

        Args:
            key: Cache key (will be namespaced automatically)
            value: Value to cache
            l2_ttl: TTL for L2 cache in seconds
        """
        await self.init_cache()
        await self._set_both_layers(key, value, l2_ttl)

    async def delete(self, key: str):
        """
        Delete a key from both cache layers.

        Always deletes from both layers, even under pressure.
        Deleting from Redis is critical to prevent stale data.
        """
        await self.init_cache()

        l1_key = self._l1_key(key)
        l2_key = self._l2_key(key)

        # Always delete from L1
        self.l1.pop(l1_key, None)

        # Always delete from Redis (critical for consistency)
        if self._redis:
            try:
                await self._redis.delete(l2_key)
                logger.debug("Deleted from both layers", key=key)
            except RedisError as e:
                logger.error(f"Redis DELETE error: {e}", key=key)
                self.stats["errors"] += 1

    async def delete_pattern(self, pattern: str):
        """
        Delete all keys matching a pattern (L2 only).

        L1 is process-local and will expire naturally.
        """
        await self.init_cache()

        if not self._redis:
            return

        try:
            l2_pattern = self._l2_key(pattern)
            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = await self._redis.scan(
                    cursor, match=l2_pattern, count=100
                )
                if keys:
                    await self._redis.delete(*keys)
                    deleted_count += len(keys)
                if cursor == 0:
                    break

            logger.info(
                "Pattern delete completed", pattern=pattern, deleted=deleted_count
            )

        except RedisError as e:
            logger.error(f"Pattern delete error: {e}", pattern=pattern)
            self.stats["errors"] += 1

    async def close(self):
        """Graceful shutdown of cache connections."""
        if self._redis:
            try:
                await self._redis.aclose()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis: {e}")

    def get_stats(self) -> dict:
        """Get cache statistics including memory pressure."""
        total = sum(
            [self.stats["l1_hits"], self.stats["l2_hits"], self.stats["misses"]]
        )

        stats = {
            **self.stats,
            "l1_size": len(self.l1) if self.l1 else 0,
            "l1_maxsize": self.l1.maxsize if self.l1 else 0,
            "hit_rate": (
                (self.stats["l1_hits"] + self.stats["l2_hits"]) / total
                if total > 0
                else 0
            ),
        }

        # Add current memory pressure if available
        if self._memory_guard and self._memory_guard._cached:
            stats["redis_pressure"] = self._memory_guard._cached

        return stats


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


# Cache layer instance (singleton per worker)
cache_layer = CacheLayer()
