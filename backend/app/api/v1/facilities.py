"""
Facility API endpoints.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.schemas.facility import FacilityResponse
from app.services.facility import FacilityService

router = APIRouter()


@router.get("/facilities", response_model=PaginatedResponse[FacilityResponse])
async def list_facilities(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=500, description="Items per page"),
    type: Optional[str] = Query(None, description="Filter by facility type"),
    state: Optional[str] = Query(None, description="Filter by state"),
    city: Optional[str] = Query(None, description="Filter by city"),
    country: Optional[str] = Query(None, description="Filter by country"),
    db: AsyncSession = Depends(get_db),
):
    """List facilities with optional filters and pagination."""
    service = FacilityService(db)
    items, total = await service.list(
        page=page,
        page_size=page_size,
        type=type,
        state=state,
        city=city,
        country=country,
    )
    return PaginatedResponse(
        data=[FacilityResponse.model_validate(f) for f in items],
        pagination=PaginationMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/facilities/summary")
async def get_facilities_summary(
    db: AsyncSession = Depends(get_db),
):
    """Get facility type distribution summary counts."""
    service = FacilityService(db)
    items, total = await service.list(page=1, page_size=500)
    type_counts = {}
    for f in items:
        ftype = f.type or "Industrial Facility"
        type_counts[ftype] = type_counts.get(ftype, 0) + 1
    return {
        "totalFacilities": total,
        "typeDistribution": type_counts
    }


@router.get("/facilities/{facility_id}", response_model=FacilityResponse)
async def get_facility(
    facility_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single facility by ID."""
    service = FacilityService(db)
    facility = await service.get_by_id(facility_id)
    return FacilityResponse.model_validate(facility)
