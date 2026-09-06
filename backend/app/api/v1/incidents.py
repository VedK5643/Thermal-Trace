"""
Incident API endpoints.
Incidents are derived from hotspot+facility joins (no separate DB table).
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.schemas.incident import IncidentResponse
from app.services.incident import IncidentService

router = APIRouter()


@router.get("/incidents", response_model=PaginatedResponse[IncidentResponse])
async def list_incidents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=500, description="Items per page"),
    type: Optional[str] = Query(None, description="Filter by hotspot type"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    min_confidence: Optional[float] = Query(None, ge=0, le=100, description="Minimum confidence"),
    state: Optional[str] = Query(None, description="Filter by state"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    db: AsyncSession = Depends(get_db),
):
    """List incidents (derived from hotspot+facility data) with filters."""
    service = IncidentService(db)
    items, total = await service.list(
        page=page,
        page_size=page_size,
        type=type,
        severity=severity,
        min_confidence=min_confidence,
        state=state,
        start_date=start_date,
        end_date=end_date,
    )
    return PaginatedResponse(
        data=[IncidentResponse.model_validate(i) for i in items],
        pagination=PaginationMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/incidents/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single incident by ID (derived from hotspot+facility)."""
    service = IncidentService(db)
    incident = await service.get_by_id(incident_id)
    return IncidentResponse.model_validate(incident)
