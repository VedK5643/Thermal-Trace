"""
Health check endpoint.
"""
import logging

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.redis import redis_manager
from app.services.firms_status import firms_sync_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.api_route("/health", methods=["GET", "HEAD"])
async def health_check(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    Application health check.
    Returns app status, database connectivity, Redis ping status, and FIRMS sync status summary.
    """
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error("Database health check failed: %s", str(e))
        db_status = "unavailable"

    redis_ok = await redis_manager.ping()
    redis_status = "healthy" if redis_ok else "unhealthy"

    status = "healthy" if db_status == "healthy" and redis_status == "healthy" else "degraded"

    background_tasks.add_task(firms_sync_manager.execute_sync_if_needed)

    firms_status = firms_sync_manager.get_status_payload()

    return {
        "status": status,
        "service": "thermalwatch-api",
        "version": "0.1.0",
        "database": db_status,
        "redis": redis_status,
        "firms": {
            "status": firms_status["status"],
            "lastSyncSuccessAt": firms_status["lastSyncSuccessAt"],
            "latestObservationAt": firms_status["latestObservationAt"]
        }
    }
