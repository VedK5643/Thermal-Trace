"""
Alert API endpoints.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.schemas.alert import AlertResponse
from app.services.alert import AlertService

router = APIRouter()


@router.get("/alerts", response_model=PaginatedResponse[AlertResponse])
async def list_alerts(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=500, description="Items per page"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledged status"),
    date: Optional[str] = Query(None, description="Filter by IST date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
):
    """List alerts with optional filters and pagination."""
    service = AlertService(db)
    items, total = await service.list(
        page=page,
        page_size=page_size,
        severity=severity,
        acknowledged=acknowledged,
        date_str=date,
    )
    return PaginatedResponse(
        data=[AlertResponse.model_validate(a) for a in items],
        pagination=PaginationMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single alert by ID."""
    service = AlertService(db)
    alert = await service.get_by_id(alert_id)
    return AlertResponse.model_validate(alert)
