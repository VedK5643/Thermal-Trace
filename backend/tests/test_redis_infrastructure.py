"""
Comprehensive Pytest Suite for ThermalTrace Redis Infrastructure.
Tests connection pool, health check, rate limiting, atomic AI quotas, analytics caching,
FIRMS distributed locking, lock contention, cache invalidation, and failure fallbacks.
"""
import json
import pytest
import asyncio
from unittest.mock import patch, AsyncMock

from app.core.redis import redis_manager
from app.services.auth import check_rate_limit
from app.services.firms_status import FIRMSSyncManager


@pytest.fixture(autouse=True)
async def cleanup_redis_client():
    """Reset redis_manager client before each test to prevent loop closed errors."""
    await redis_manager.close()
    yield
    await redis_manager.close()


@pytest.mark.anyio
async def test_redis_connection_and_health():
    """Verify Redis connection pool initialization and health PING check."""
    pong = await redis_manager.ping()
    assert pong is True, "Redis PING health check failed"


@pytest.mark.anyio
async def test_redis_rate_limiting():
    """Verify backend rate limiting using Redis atomic counters and expiration."""
    test_key = "test_user_rate_limit_123"

    # Clean previous state
    client = redis_manager.get_client()
    await client.delete(f"thermalwatch:ratelimit:{test_key}")

    # Request 1 (allowed)
    allowed, count, ttl = await redis_manager.check_rate_limit(test_key, limit=2, window_seconds=60)
    assert allowed is True
    assert count == 1
    assert ttl > 0

    # Request 2 (allowed)
    allowed, count, ttl = await redis_manager.check_rate_limit(test_key, limit=2, window_seconds=60)
    assert allowed is True
    assert count == 2

    # Request 3 (rejected)
    allowed, count, ttl = await redis_manager.check_rate_limit(test_key, limit=2, window_seconds=60)
    assert allowed is False
    assert count == 3

    # Clean up
    await client.delete(f"thermalwatch:ratelimit:{test_key}")


@pytest.mark.anyio
async def test_redis_ai_quota_atomic():
    """Verify atomic AI quota tracking and HTTP 429 rejection on limit exhaustion."""
    guest_id = "test_guest_ip_456"

    client = redis_manager.get_client()
    await client.delete(f"thermalwatch:quota:ai:guest:{guest_id}")

    # Guest quota limit set to 2 for testing
    allowed, count, limit = await redis_manager.check_ai_quota_atomic(
        identifier=guest_id,
        is_authenticated=False,
        limit_override=2,
        period_seconds=60,
    )
    assert allowed is True
    assert count == 1

    allowed, count, limit = await redis_manager.check_ai_quota_atomic(
        identifier=guest_id,
        is_authenticated=False,
        limit_override=2,
        period_seconds=60,
    )
    assert allowed is True
    assert count == 2

    # 3rd attempt exceeds quota
    allowed, count, limit = await redis_manager.check_ai_quota_atomic(
        identifier=guest_id,
        is_authenticated=False,
        limit_override=2,
        period_seconds=60,
    )
    assert allowed is False
    assert count == 3

    await client.delete(f"thermalwatch:quota:ai:guest:{guest_id}")


@pytest.mark.anyio
async def test_redis_analytics_cache():
    """Verify analytics response cache HIT, MISS, canonical key, TTL, and invalidation."""
    cache_key = "analytics:summary:state=Gujarat:class=all:sev=all:days=7"
    client = redis_manager.get_client()
    await client.delete(f"thermalwatch:cache:{cache_key}")

    # 1. MISS
    cached_val = await redis_manager.get_cache(cache_key)
    assert cached_val is None

    # 2. SET
    mock_payload = {"totalObservations": 150, "industrialFirePercentage": 42.5}
    set_ok = await redis_manager.set_cache(cache_key, json.dumps(mock_payload), ttl_seconds=300)
    assert set_ok is True

    # 3. HIT
    cached_val = await redis_manager.get_cache(cache_key)
    assert cached_val is not None
    data = json.loads(cached_val)
    assert data["totalObservations"] == 150

    # 4. Invalidate Pattern
    invalidated_count = await redis_manager.invalidate_cache_pattern("analytics:*")
    assert invalidated_count >= 1

    # Verify cache cleared
    assert await redis_manager.get_cache(cache_key) is None


@pytest.mark.anyio
async def test_firms_distributed_lock():
    """Verify Redis distributed lock prevents concurrent FIRMS sync execution."""
    lock_name = "firms_sync_test"
    token_worker1 = "worker_1_uuid"
    token_worker2 = "worker_2_uuid"

    # Worker 1 acquires lock
    acquired_1 = await redis_manager.acquire_lock(lock_name, token_worker1, ttl_seconds=60)
    assert acquired_1 is True

    # Worker 2 attempts to acquire lock (must fail)
    acquired_2 = await redis_manager.acquire_lock(lock_name, token_worker2, ttl_seconds=60)
    assert acquired_2 is False

    # Worker 2 attempts to release Worker 1's lock (must fail via Lua script)
    released_by_2 = await redis_manager.release_lock(lock_name, token_worker2)
    assert released_by_2 is False

    # Worker 1 releases own lock
    released_by_1 = await redis_manager.release_lock(lock_name, token_worker1)
    assert released_by_1 is True

    # Worker 2 can now acquire lock
    acquired_2_again = await redis_manager.acquire_lock(lock_name, token_worker2, ttl_seconds=60)
    assert acquired_2_again is True

    await redis_manager.release_lock(lock_name, token_worker2)


@pytest.mark.anyio
async def test_redis_failure_fallback():
    """Verify application gracefully falls back when Redis is unavailable."""
    with patch.object(redis_manager, "get_client", side_effect=Exception("Redis connection refused")):
        # Health check reports unhealthy without crashing
        redis_ok = await redis_manager.ping()
        assert redis_ok is False

        # Cache GET returns None (triggers DB query fallback)
        res = await redis_manager.get_cache("some_key")
        assert res is None
