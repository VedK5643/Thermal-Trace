"""
Ingestion API endpoints.

POST /api/v1/ingestion/firms
    Trigger a FIRMS data ingest for a single source (source, bbox, days queryparams).
    Returns a per-source ingest summary.

POST /api/v1/ingestion/firms/all
    Trigger a multi-source FIRMS ingest across all configured VIIRS NRT satellites.
    Uses settings.firms_source_list and settings.firms_ingestion_days by default.
    Supports failure isolation — one source failing does not block others.
    Returns an aggregated multi-source summary.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.integrations.firms.client import INDIA_BBOX
from app.integrations.firms.service import FIRMSIngestionService

router = APIRouter()
logger = logging.getLogger(__name__)


def _require_firms_key() -> None:
    """Raise 503 if FIRMS_MAP_KEY is not configured."""
    if not settings.firms_map_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FIRMS_MAP_KEY is not configured. Set it in backend/.env",
        )


# ---------------------------------------------------------------------------
# Single-source endpoint (Phase 5 baseline — preserved unchanged)
# ---------------------------------------------------------------------------

from sqlalchemy import select, func
from app.db.models.hotspot import Hotspot
from app.services.firms_status import firms_sync_manager

@router.post(
    "/ingestion/firms",
    status_code=status.HTTP_200_OK,
    summary="Trigger NASA FIRMS data ingestion (single source)",
    description=(
        "Fetches real satellite thermal data from NASA FIRMS for a single source "
        "and upserts it into the hotspots table. Safe to call repeatedly — "
        "duplicate observations are silently skipped. "
        "Use POST /ingestion/firms/all for multi-source India-wide coverage."
    ),
)
async def ingest_firms(
    source: str = Query(
        "VIIRS_SNPP_NRT",
        description="FIRMS data source. Options: VIIRS_SNPP_NRT, VIIRS_NOAA20_NRT, VIIRS_NOAA21_NRT, MODIS_NRT",
    ),
    bbox: str = Query(
        INDIA_BBOX,
        description="Bounding box: west,south,east,north (WGS-84)",
    ),
    days: int = Query(
        None,
        ge=1,
        le=10,
        description=(
            "Number of past days to fetch (1-10). "
            "Defaults to FIRMS_INGESTION_DAYS setting (currently configured as 5)."
        ),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger NASA FIRMS ingestion for the specified source, bounding box, and day range.
    """
    _require_firms_key()

    effective_days = days if days is not None else settings.firms_ingestion_days

    try:
        service = FIRMSIngestionService(db=db, map_key=settings.firms_map_key)
        summary = await service.ingest(source=source, bbox=bbox, days=effective_days)

        stmt = select(func.max(Hotspot.timestamp))
        max_res = await db.execute(stmt)
        max_ts = max_res.scalar()
        await firms_sync_manager.record_sync_success(
            inserted=summary.get("inserted", 0),
            latest_ts=max_ts,
        )
    except Exception as exc:
        logger.error("FIRMS ingest error: %s", exc, exc_info=True)
        firms_sync_manager.record_sync_failure(str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"FIRMS ingest failed: {exc}",
        ) from exc

    return summary


# ---------------------------------------------------------------------------
# Multi-source endpoint (Phase 5D — maximum India-wide coverage)
# ---------------------------------------------------------------------------

@router.post(
    "/ingestion/firms/all",
    status_code=status.HTTP_200_OK,
    summary="Trigger NASA FIRMS multi-source India-wide ingestion",
    description=(
        "Fetches real satellite thermal data from all configured VIIRS NRT sources "
        "(VIIRS_SNPP_NRT, VIIRS_NOAA20_NRT, VIIRS_NOAA21_NRT) for the configured "
        "ingestion window (FIRMS_INGESTION_DAYS, default 5 days). "
        "If one satellite source fails, data from the others is still persisted. "
        "All observations are deduplicated by stable SHA-256 fingerprint. "
        "Safe to call repeatedly — duplicates are silently skipped."
    ),
)
async def ingest_firms_all_sources(
    bbox: str = Query(
        INDIA_BBOX,
        description="Bounding box: west,south,east,north (WGS-84). Default covers all of India.",
    ),
    days: int = Query(
        None,
        ge=1,
        le=10,
        description=(
            "Number of past days to ingest (1–10). "
            "Defaults to FIRMS_INGESTION_DAYS setting."
        ),
    ),
    sources: str = Query(
        None,
        description=(
            "Comma-separated FIRMS source list. "
            "Defaults to FIRMS_SOURCES setting (VIIRS_SNPP_NRT,VIIRS_NOAA20_NRT,VIIRS_NOAA21_NRT)."
        ),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger NASA FIRMS multi-source ingestion for maximum India-wide coverage.
    """
    _require_firms_key()

    effective_days = days if days is not None else settings.firms_ingestion_days
    effective_sources = (
        [s.strip() for s in sources.split(",") if s.strip()]
        if sources
        else settings.firms_source_list
    )

    if not effective_sources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No FIRMS sources configured. Set FIRMS_SOURCES in backend/.env",
        )

    logger.info(
        "Multi-source FIRMS ingestion triggered: sources=%s bbox=%s days=%d",
        effective_sources, bbox, effective_days,
    )

    try:
        service = FIRMSIngestionService(db=db, map_key=settings.firms_map_key)
        summary = await service.ingest_all_sources(
            sources=effective_sources, bbox=bbox, days=effective_days
        )

        stmt = select(func.max(Hotspot.timestamp))
        max_res = await db.execute(stmt)
        max_ts = max_res.scalar()

        if summary.get("sources_succeeded", 0) > 0 or summary.get("total_fetched", 0) > 0 or summary.get("total_inserted", 0) > 0:
            await firms_sync_manager.record_sync_success(
                inserted=summary.get("total_inserted", 0),
                latest_ts=max_ts,
            )
        elif summary.get("sources_failed", 0) > 0:
            err_msg = "; ".join(e.get("error", "") for e in summary.get("errors", []))
            firms_sync_manager.record_sync_failure(err_msg)
    except Exception as exc:
        logger.error("Multi-source FIRMS ingest error: %s", exc, exc_info=True)
        firms_sync_manager.record_sync_failure(str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Multi-source FIRMS ingest failed: {exc}",
        ) from exc

    return summary
