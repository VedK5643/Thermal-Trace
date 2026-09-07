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

FORWARD_TYPE_MAPPING = {
    "landuse_industrial": "industrial",
    "landuse_quarry": "quarry",
    "man_made_chimney": "chimney",
    "power_plant": "power plant",
    "man_made_works": "works"
}

def map_osm_feature_to_response(f) -> FacilityResponse:
    canonical_type = FORWARD_TYPE_MAPPING.get(f.feature_type, f.feature_type)
    return FacilityResponse(
        id=f.id,
        name=f.name or "Unknown Facility",
        type=canonical_type,
        rawType=f.feature_type,
        latitude=f.latitude,
        longitude=f.longitude,
        city="Unknown",
        state="Unknown",
        country="India",
        source="osm",
        osm_type=f.osm_type,
        osm_id=f.osm_id,
        raw_tags=f.raw_tags
    )


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
        data=[map_osm_feature_to_response(f) for f in items],
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
        canonical_type = FORWARD_TYPE_MAPPING.get(f.feature_type, f.feature_type)
        type_counts[canonical_type] = type_counts.get(canonical_type, 0) + 1
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
    if not facility:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Facility not found")
    return map_osm_feature_to_response(facility)

