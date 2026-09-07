"""
Facility repository — database access layer for facility queries.
"""
import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.osm_feature import OSMFeature

logger = logging.getLogger(__name__)

# Allowed facility types for this endpoint
ALLOWED_FEATURE_TYPES = [
    "landuse_industrial",
    "landuse_quarry",
    "man_made_chimney",
    "power_plant",
    "man_made_works"
]

REVERSE_TYPE_MAPPING = {
    "industrial": "landuse_industrial",
    "quarry": "landuse_quarry",
    "chimney": "man_made_chimney",
    "power plant": "power_plant",
    "works": "man_made_works"
}

class FacilityRepository:
    """Repository for facility database operations using OSMFeatures."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, facility_id: str) -> Optional[OSMFeature]:
        """Get a single facility by ID."""
        result = await self.db.execute(
            select(OSMFeature).where(OSMFeature.id == facility_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 100,
        type: Optional[str] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        country: Optional[str] = None,
    ) -> tuple[list[OSMFeature], int]:
        """
        List facilities with optional filters and pagination.
        Returns (items, total_count).
        """
        query = select(OSMFeature).where(OSMFeature.feature_type.in_(ALLOWED_FEATURE_TYPES))
        count_query = select(func.count()).select_from(OSMFeature).where(OSMFeature.feature_type.in_(ALLOWED_FEATURE_TYPES))

        if type is not None:
            # Reverse map the normalized type to the DB feature_type
            db_type = REVERSE_TYPE_MAPPING.get(type, type)
            query = query.where(OSMFeature.feature_type == db_type)
            count_query = count_query.where(OSMFeature.feature_type == db_type)
            
        # Ignore state, city, country filters as OSMFeature doesn't have them
        # (Preserved in arguments to keep service interface intact)

        # Order by id to ensure stable pagination
        query = query.order_by(OSMFeature.id)

        # Pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return items, total

