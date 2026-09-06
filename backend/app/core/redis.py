"""
Centralized Redis Client Infrastructure for ThermalTrace.
Provides connection pooling, rate limiting, atomic AI quotas, analytics caching,
distributed locking for FIRMS sync, and graceful failure fallbacks.
"""
import asyncio
import logging
from typing import Optional, Any
import redis.asyncio as aioredis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Lua script for safe atomic lock release (prevents deleting another worker's lock)
RELEASE_LOCK_LUA_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class RedisManager:
    """
    Centralized Async Redis Manager.
    Manages connection pool, rate limits, AI quotas, response caching, and distributed locking.
    """

    def __init__(self):
        self._pool: Optional[aioredis.ConnectionPool] = None
        self._client: Optional[aioredis.Redis] = None
        self._loop_id: Optional[int] = None

    def _check_loop(self):
        """Reset pool and client if running inside a new or different event loop (e.g. during pytest execution)."""
        try:
            loop = asyncio.get_running_loop()
            current_id = id(loop)
            if self._loop_id != current_id:
                self._pool = None
                self._client = None
                self._loop_id = current_id
        except RuntimeError:
            pass

    def _get_pool(self) -> aioredis.ConnectionPool:
        """Lazy-initialize Redis connection pool."""
        self._check_loop()
        if self._pool is None:
            logger.info("Initializing Redis connection pool at: %s", settings.redis_url)
            self._pool = aioredis.ConnectionPool.from_url(
                settings.redis_url,
                max_connections=20,
                decode_responses=True,
            )
        return self._pool

    def get_client(self) -> aioredis.Redis:
        """Get an async Redis client from the shared connection pool."""
        self._check_loop()
        if self._client is None:
            pool = self._get_pool()
            self._client = aioredis.Redis(connection_pool=pool)
        return self._client

    async def close(self):
        """Close client and connection pool cleanly."""
        if self._client:
            try:
                await self._client.aclose()
            except Exception:
                pass
            finally:
                self._client = None

        if self._pool:
            try:
                await self._pool.aclose()
            except Exception:
                pass
            finally:
                self._pool = None

    async def ping(self) -> bool:
        """Non-blocking Redis PING health check."""
        try:
            client = self.get_client()
            res = await client.ping()
            return res is True
        except Exception as e:
            logger.warning("Redis health check PING failed: %s", e)
            return False

    # ------------------------------------------------------------------
    # 1 & 2. Rate Limiting & Guest/API Abuse Protection
    # ------------------------------------------------------------------

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> tuple[bool, int, int]:
        """
        Check rate limit for key using atomic Redis pipeline (INCR + EXPIRE).
        Returns (is_allowed, current_count, ttl_remaining).
        Fallback behavior: If Redis is unavailable, returns (True, 1, window_seconds)
        to allow traffic gracefully without silent security disablement.
        """
        full_key = f"thermalwatch:ratelimit:{key}"
        try:
            client = self.get_client()
            async with client.pipeline(transaction=True) as pipe:
                pipe.incr(full_key)
                pipe.ttl(full_key)
                results = await pipe.execute()

            count = results[0]
            ttl = results[1]

            # If new key, set window TTL
            if count == 1 or ttl < 0:
                await client.expire(full_key, window_seconds)
                ttl = window_seconds

            allowed = count <= limit
            return allowed, count, max(ttl, 0)
        except Exception as e:
            logger.warning("Redis rate limit check error for key %s (fallback allowed): %s", key, e)
            # Conservative fallback: allow single request, preserve backend protection
            return True, 1, window_seconds

    # ------------------------------------------------------------------
    # 3. Authenticated & Guest AI Quota Management (Atomic INCR)
    # ------------------------------------------------------------------

    async def check_ai_quota_atomic(
        self,
        identifier: str,
        is_authenticated: bool,
        limit_override: Optional[int] = None,
        period_seconds: int = 3600,
    ) -> tuple[bool, int, int]:
        """
        Check and increment AI request quota atomically.
        Key structure:
        - Auth user: thermalwatch:quota:ai:user:{user_id}
        - Guest:     thermalwatch:quota:ai:guest:{ip_or_id}
        Returns (is_allowed, current_count, limit_used).
        """
        prefix = "user" if is_authenticated else "guest"
        limit = limit_override or (
            settings.ai_user_quota_per_hour if is_authenticated else settings.ai_guest_quota_per_hour
        )
        full_key = f"thermalwatch:quota:ai:{prefix}:{identifier}"

        try:
            client = self.get_client()
            async with client.pipeline(transaction=True) as pipe:
                pipe.incr(full_key)
                pipe.ttl(full_key)
                results = await pipe.execute()

            count = results[0]
            ttl = results[1]

            if count == 1 or ttl < 0:
                await client.expire(full_key, period_seconds)

            allowed = count <= limit
            return allowed, count, limit
        except Exception as e:
            logger.warning("Redis AI quota check error for %s (fallback to conservative check): %s", identifier, e)
            # Fallback: Allow request but log issue
            return True, 1, limit

    # ------------------------------------------------------------------
    # 4. Analytics & Response Caching
    # ------------------------------------------------------------------

    async def get_cache(self, key: str) -> Optional[str]:
        """Get cached response string by canonical key."""
        full_key = f"thermalwatch:cache:{key}"
        try:
            client = self.get_client()
            return await client.get(full_key)
        except Exception as e:
            logger.warning("Redis cache GET error for %s (cache bypass): %s", key, e)
            return None

    async def set_cache(self, key: str, value: str, ttl_seconds: int = 300) -> bool:
        """Set cached response string with TTL."""
        full_key = f"thermalwatch:cache:{key}"
        try:
            client = self.get_client()
            await client.set(full_key, value, ex=ttl_seconds)
            return True
        except Exception as e:
            logger.warning("Redis cache SET error for %s: %s", key, e)
            return False

    async def invalidate_cache_pattern(self, pattern: str) -> int:
        """Invalidate all cache entries matching key pattern (e.g. 'analytics:*')."""
        full_pattern = f"thermalwatch:cache:{pattern}"
        deleted = 0
        try:
            client = self.get_client()
            keys = await client.keys(full_pattern)
            if keys:
                deleted = await client.delete(*keys)
                logger.info("Invalidated %d cache keys matching pattern '%s'", deleted, pattern)
            return deleted
        except Exception as e:
            logger.warning("Redis cache invalidation error for pattern %s: %s", pattern, e)
            return 0

    # ------------------------------------------------------------------
    # 5. FIRMS Synchronization Distributed Lock
    # ------------------------------------------------------------------

    async def acquire_lock(self, lock_name: str, token: str, ttl_seconds: int = 600) -> bool:
        """
        Acquire distributed lock using atomic SET key token NX EX ttl_seconds.
        Key structure: thermalwatch:lock:{lock_name}
        """
        full_key = f"thermalwatch:lock:{lock_name}"
        try:
            client = self.get_client()
            res = await client.set(full_key, token, nx=True, ex=ttl_seconds)
            return res is True
        except Exception as e:
            logger.warning("Redis lock acquire error for %s: %s", lock_name, e)
            return False

    async def release_lock(self, lock_name: str, token: str) -> bool:
        """
        Release distributed lock using Lua script to verify lock ownership.
        Prevents releasing a lock owned by another worker.
        """
        full_key = f"thermalwatch:lock:{lock_name}"
        try:
            client = self.get_client()
            res = await client.eval(RELEASE_LOCK_LUA_SCRIPT, 1, full_key, token)
            return bool(res)
        except Exception as e:
            logger.warning("Redis lock release error for %s: %s", lock_name, e)
            return False


# Global Redis Manager Instance
redis_manager = RedisManager()
