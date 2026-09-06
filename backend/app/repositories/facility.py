"""
Facility repository — database access layer for facility queries.
"""
import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.facility import Facility

logger = logging.getLogger(__name__)


class FacilityRepository:
    """Repository for facility database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, facility_id: str) -> Optional[Facility]:
        """Get a single facility by ID."""
        result = await self.db.execute(
            select(Facility).where(Facility.id == facility_id)
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
    ) -> tuple[list[Facility], int]:
        """
        List facilities with optional filters and pagination.
        Returns (items, total_count).
        """
        query = select(Facility)
        count_query = select(func.count()).select_from(Facility)

        if type is not None:
            query = query.where(Facility.type == type)
            count_query = count_query.where(Facility.type == type)
        if state is not None:
            query = query.where(Facility.state == state)
            count_query = count_query.where(Facility.state == state)
        if city is not None:
            query = query.where(Facility.city == city)
            count_query = count_query.where(Facility.city == city)
        if country is not None:
            query = query.where(Facility.country == country)
            count_query = count_query.where(Facility.country == country)

        # Order by name
        query = query.order_by(Facility.name)

        # Pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return items, total
