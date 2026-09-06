"""
Hotspot API endpoints.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.schemas.hotspot import HotspotResponse, ActivityResponse
from app.services.hotspot import HotspotService

router = APIRouter()


@router.get("/hotspots", response_model=PaginatedResponse[HotspotResponse], response_model_by_alias=True)
async def list_hotspots(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=2000, description="Items per page (max 2000 to support full India-wide multi-source FIRMS dataset)"),
    type: Optional[str] = Query(None, description="Filter by hotspot type"),
    min_confidence: Optional[float] = Query(None, ge=0, le=100, description="Minimum confidence"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    state: Optional[str] = Query(None, description="Filter by state"),
    city: Optional[str] = Query(None, description="Filter by city"),
    country: Optional[str] = Query(None, description="Filter by country"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    near_lat: Optional[float] = Query(None, ge=-90, le=90, description="Spatial query center latitude"),
    near_lng: Optional[float] = Query(None, ge=-180, le=180, description="Spatial query center longitude"),
    radius_km: Optional[float] = Query(None, ge=0.1, le=5000, description="Spatial query radius in km"),
    db: AsyncSession = Depends(get_db),
):
    """List hotspots with optional filters, PostGIS spatial radius search, and pagination."""
    if end_date and end_date.hour == 0 and end_date.minute == 0 and end_date.second == 0:
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    service = HotspotService(db)
    items, total = await service.list(
        page=page,
        page_size=page_size,
        type=type,
        min_confidence=min_confidence,
        severity=severity,
        state=state,
        city=city,
        country=country,
        start_date=start_date,
        end_date=end_date,
        near_lat=near_lat,
        near_lng=near_lng,
        radius_km=radius_km,
    )
    return PaginatedResponse(
        data=[HotspotResponse.model_validate(h) for h in items],
        pagination=PaginationMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/hotspots/latest-date")
async def get_latest_date(db: AsyncSession = Depends(get_db)):
    """Get the most recent date available in the database."""
    service = HotspotService(db)
    latest_ts = await service.repo.get_latest_date()

    ist_tz = timezone(timedelta(hours=5, minutes=30))
    if latest_ts:
        if latest_ts.tzinfo is None:
            latest_ts = latest_ts.replace(tzinfo=timezone.utc)
        ist_date = latest_ts.astimezone(ist_tz)
        return {"date": ist_date.strftime("%Y-%m-%d")}
    return {"date": datetime.now(ist_tz).strftime("%Y-%m-%d")}


@router.get("/hotspots/activity", response_model=ActivityResponse)
async def get_hotspot_activity(
    end_date: datetime = Query(..., description="End date (typically current active map date)"),
    min_confidence: Optional[float] = Query(None, ge=0, le=100, description="Minimum confidence"),
    state: Optional[str] = Query(None, description="Filter by state"),
    city: Optional[str] = Query(None, description="Filter by city"),
    country: Optional[str] = Query(None, description="Filter by country"),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated 7-day activity ending on end_date."""
    # Ensure end_date covers the entire day if time is midnight
    if end_date.hour == 0 and end_date.minute == 0 and end_date.second == 0:
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    service = HotspotService(db)
    activity_data = await service.get_activity(
        end_date=end_date,
        min_confidence=min_confidence,
        state=state,
        city=city,
        country=country,
    )
    return ActivityResponse.model_validate(activity_data)


@router.get("/hotspots/{hotspot_id}", response_model=HotspotResponse)
async def get_hotspot(
    hotspot_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single hotspot by ID."""
    service = HotspotService(db)
    hotspot = await service.get_by_id(hotspot_id)
    return HotspotResponse.model_validate(hotspot)
