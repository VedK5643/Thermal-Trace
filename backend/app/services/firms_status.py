"""
FIRMS Synchronization & Status Manager for ThermalTrace.
Manages backend-owned sync timestamps, single-concurrency lock, 6-hour scheduled cadence, freshness status evaluation, background scheduler task, and health integration.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import redis_manager
from app.db.models.hotspot import Hotspot
from app.db.session import async_session_factory
from app.integrations.firms.service import FIRMSIngestionService

logger = logging.getLogger(__name__)

IST_OFFSET = timezone(timedelta(hours=5, minutes=30))


def get_next_scheduled_sync_time(last_success: Optional[datetime] = None) -> datetime:
    """Calculate the next scheduled sync time based on 6-hour interval."""
    now_utc = datetime.now(timezone.utc)
    base_dt = last_success or now_utc
    if base_dt.tzinfo is None:
        base_dt = base_dt.replace(tzinfo=timezone.utc)
    next_sync = base_dt + timedelta(hours=settings.firms_sync_interval_hours)
    if next_sync < now_utc:
        return now_utc
    return next_sync


class FIRMSSyncManager:
    """
    Backend-controlled manager for NASA FIRMS data ingestion and sync metadata.
    Enforces concurrency lock, 6-hour scheduled interval, and status freshness classification.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self.last_sync_started_at: Optional[datetime] = None
        self.last_sync_completed_at: Optional[datetime] = None
        self.last_sync_success_at: Optional[datetime] = None
        self.last_sync_status: str = "success"  # "success", "degraded", "failed"
        self.last_sync_error: Optional[str] = None
        self.latest_observation_at: Optional[datetime] = None
        self.observations_ingested: int = 0
        self.satellites: List[str] = ["SNPP", "NOAA-20", "NOAA-21"]
        self._scheduler_task: Optional[asyncio.Task] = None
        self._scheduler_running: bool = False

    async def initialize_from_db(self):
        """Query PostgreSQL DB on startup to initialize latest observation and last sync timestamps."""
        try:
            async with async_session_factory() as db:
                stmt = select(func.max(Hotspot.timestamp))
                res = await db.execute(stmt)
                max_ts = res.scalar()
                now = datetime.now(timezone.utc)
                if max_ts:
                    if max_ts.tzinfo is None:
                        max_ts = max_ts.replace(tzinfo=timezone.utc)
                    self.latest_observation_at = max_ts
                else:
                    self.latest_observation_at = now - timedelta(hours=1)

                # Try loading last_sync_success_at from Redis key "firms:last_sync_success_at"
                saved_sync_at = await redis_manager.get_cache("firms:last_sync_success_at")
                if saved_sync_at:
                    try:
                        dt = datetime.fromisoformat(saved_sync_at)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        self.last_sync_success_at = dt
                    except Exception:
                        self.last_sync_success_at = now
                else:
                    self.last_sync_success_at = now

                self.last_sync_status = "success"
        except Exception as e:
            logger.warning("Notice initializing FIRMS status from database: %s", e)

    def get_status_classification(self) -> str:
        """
        Evaluate freshness classification:
        - "degraded": last sync attempt failed
        - "live": last successful sync within 6h
        - "delayed": last successful sync between 6h and 12h
        - "stale": last successful sync older than 12h
        """
        if self.last_sync_status in ("degraded", "failed"):
            return "degraded"

        if not self.last_sync_success_at:
            return "stale"

        now = datetime.now(timezone.utc)
        age_hours = (now - self.last_sync_success_at).total_seconds() / 3600.0

        if age_hours <= settings.firms_sync_interval_hours:
            return "live"
        elif age_hours <= settings.firms_stale_threshold_hours:
            return "delayed"
        else:
            return "stale"

    def get_status_payload(self) -> Dict[str, Any]:
        """Return lightweight status metadata payload for GET /api/v1/firms/status."""
        now = datetime.now(timezone.utc)
        next_sync = get_next_scheduled_sync_time(self.last_sync_success_at)

        return {
            "status": self.get_status_classification(),
            "lastSyncSuccessAt": self.last_sync_success_at.isoformat() if self.last_sync_success_at else None,
            "latestObservationAt": self.latest_observation_at.isoformat() if self.latest_observation_at else None,
            "nextScheduledSyncAt": next_sync.isoformat(),
            "satellites": self.satellites,
            "observationsIngested": self.observations_ingested,
            "syncIntervalHours": settings.firms_sync_interval_hours,
        }

    async def record_sync_success(self, inserted: int, latest_ts: Optional[datetime] = None):
        """Record successful synchronization state (used by manual or automated syncs)."""
        now = datetime.now(timezone.utc)
        self.last_sync_completed_at = now
        self.last_sync_success_at = now
        self.last_sync_status = "success"
        self.last_sync_error = None
        self.observations_ingested = inserted
        if latest_ts:
            if latest_ts.tzinfo is None:
                latest_ts = latest_ts.replace(tzinfo=timezone.utc)
            self.latest_observation_at = latest_ts
        await redis_manager.set_cache("firms:last_sync_success_at", now.isoformat(), ttl_seconds=2592000)
        await redis_manager.invalidate_cache_pattern("analytics:*")

    def record_sync_failure(self, error: str):
        """Record failed synchronization state without erasing previous last_sync_success_at."""
        self.last_sync_completed_at = datetime.now(timezone.utc)
        self.last_sync_status = "degraded"
        self.last_sync_error = error

    async def execute_sync_if_needed(self, force: bool = False) -> bool:
        """
        Check sync eligibility and execute single-concurrency FIRMS ingestion.
        Returns True if sync was executed, False if skipped.
        """
        now = datetime.now(timezone.utc)

        # 1. Cooldown / Interval check
        if not force and self.last_sync_success_at:
            age_hours = (now - self.last_sync_success_at).total_seconds() / 3600.0
            if age_hours < settings.firms_sync_interval_hours:
                logger.info(
                    "FIRMS sync skipped: last successful sync was %.1fh ago (interval is %dh).",
                    age_hours,
                    settings.firms_sync_interval_hours,
                )
                return False

        # 2. Redis Distributed Lock Check
        lock_token = f"worker-{uuid.uuid4().hex[:8]}"
        got_lock = await redis_manager.acquire_lock("firms_sync", lock_token, ttl_seconds=600)
        if not got_lock:
            logger.info("FIRMS sync skipped: distributed lock 'thermalwatch:lock:firms_sync' held by another worker.")
            return False

        if self._lock.locked():
            await redis_manager.release_lock("firms_sync", lock_token)
            logger.info("FIRMS sync skipped: synchronization operation is already in progress locally.")
            return False

        async with self._lock:
            self.last_sync_started_at = datetime.now(timezone.utc)
            logger.info(
                "Starting scheduled NASA FIRMS data synchronization (lock_token=%s, cadence=%dh, sources=%s, days=%d)...",
                lock_token,
                settings.firms_sync_interval_hours,
                settings.firms_source_list,
                settings.firms_ingestion_days,
            )

            try:
                if not settings.firms_map_key:
                    logger.warning("NASA FIRMS MAP KEY not configured. Scheduled sync skipped.")
                    return False

                async with async_session_factory() as db:
                    service = FIRMSIngestionService(db=db, map_key=settings.firms_map_key)
                    res = await service.ingest_all_sources(
                        sources=settings.firms_source_list,
                        days=settings.firms_ingestion_days,
                    )

                    # Update latest observation timestamp from DB
                    stmt = select(func.max(Hotspot.timestamp))
                    max_res = await db.execute(stmt)
                    max_ts = max_res.scalar()

                    await self.record_sync_success(
                        inserted=res.get("total_inserted", 0),
                        latest_ts=max_ts,
                    )

                    duration = (self.last_sync_completed_at - self.last_sync_started_at).total_seconds()
                    logger.info(
                        "NASA FIRMS 6-hour sync completed in %.2fs: fetched=%d, inserted=%d, skipped=%d, errors=%d",
                        duration,
                        res.get("total_fetched", 0),
                        res.get("total_inserted", 0),
                        res.get("total_skipped", 0),
                        len(res.get("errors", [])),
                    )
                    return True
            except Exception as e:
                self.record_sync_failure(str(e))
                duration = (datetime.now(timezone.utc) - self.last_sync_started_at).total_seconds()
                logger.error("NASA FIRMS 6-hour sync failed after %.2fs: %s", duration, e, exc_info=True)
                return False
            finally:
                await redis_manager.release_lock("firms_sync", lock_token)

    async def _scheduler_loop(self):
        """Internal background loop task executing 6-hour sync check every 60 seconds."""
        logger.info(
            "NASA FIRMS 6-hour background scheduler loop active (checking every 60s, interval %dh).",
            settings.firms_sync_interval_hours,
        )
        # Immediate sync check on startup
        try:
            await self.execute_sync_if_needed(force=False)
        except Exception as exc:
            logger.error("Error during initial FIRMS startup sync check: %s", exc)

        while self._scheduler_running:
            try:
                await asyncio.sleep(60)
                if self._scheduler_running:
                    await self.execute_sync_if_needed(force=False)
            except asyncio.CancelledError:
                logger.info("NASA FIRMS background scheduler task cancelled.")
                break
            except Exception as exc:
                logger.error("Error in NASA FIRMS background scheduler loop: %s", exc)

    def start_scheduler_task(self):
        """Start the background 6-hour FIRMS synchronization task loop."""
        if self._scheduler_running and self._scheduler_task and not self._scheduler_task.done():
            logger.info("NASA FIRMS scheduler task already running.")
            return

        self._scheduler_running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("NASA FIRMS 6-hour background scheduler task launched.")

    def stop_scheduler_task(self):
        """Stop the background 6-hour FIRMS synchronization task loop gracefully."""
        self._scheduler_running = False
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
            logger.info("NASA FIRMS background scheduler task stop requested.")


firms_sync_manager = FIRMSSyncManager()
