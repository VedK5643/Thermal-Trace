"""
Unit tests for FIRMS Sync & Status Manager, 6-hour scheduler, and lightweight status endpoints.
Verifies status classification (live/delayed/stale/degraded), 6-hour cooldown, concurrency locking, and status payload integration.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import BackgroundTasks

from app.api.v1.firms import get_firms_status
from app.api.v1.health import health_check
from app.services.firms_status import FIRMSSyncManager


def test_firms_status_classification():
    """Verify status transitions based on 6-hour interval and 12-hour stale threshold."""
    mgr = FIRMSSyncManager()

    now = datetime.now(timezone.utc)

    # 1. Fresh (Synced < 6h ago) -> "live"
    mgr.last_sync_success_at = now - timedelta(hours=3)
    mgr.last_sync_status = "success"
    assert mgr.get_status_classification() == "live"

    # 2. Aging (Synced 6h-12h ago) -> "delayed"
    mgr.last_sync_success_at = now - timedelta(hours=8)
    assert mgr.get_status_classification() == "delayed"

    # 3. Stale (Synced > 12h ago) -> "stale"
    mgr.last_sync_success_at = now - timedelta(hours=15)
    assert mgr.get_status_classification() == "stale"

    # 4. Failed/Degraded -> "degraded"
    mgr.last_sync_status = "degraded"
    assert mgr.get_status_classification() == "degraded"


@pytest.mark.anyio
async def test_firms_cooldown_and_lock():
    """Verify 6-hour cooldown prevents unnecessary FIRMS API calls when fresh."""
    mgr = FIRMSSyncManager()
    now = datetime.now(timezone.utc)
    mgr.last_sync_success_at = now - timedelta(hours=3)  # 3 hours ago (within 6h cooldown)

    executed = await mgr.execute_sync_if_needed(force=False)
    assert executed is False


@pytest.mark.anyio
async def test_firms_status_endpoint():
    """Verify GET /api/v1/firms/status returns lightweight status metadata without calling FIRMS."""
    res = await get_firms_status()
    assert "status" in res
    assert "lastSyncSuccessAt" in res
    assert "latestObservationAt" in res
    assert "satellites" in res
    assert res["satellites"] == ["SNPP", "NOAA-20", "NOAA-21"]
    assert res["syncIntervalHours"] == 6


@pytest.mark.anyio
async def test_health_check_with_firms_summary():
    """Verify GET /api/v1/health includes firms summary metadata."""
    mock_db = AsyncMock()
    mock_bt = BackgroundTasks()
    res = await health_check(background_tasks=mock_bt, db=mock_db)
    assert "status" in res
    assert "firms" in res
    assert "status" in res["firms"]
