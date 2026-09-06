"""
Facility service — business logic layer.
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.facility import Facility
from app.repositories.facility import FacilityRepository


class FacilityService:
    """Business logic for facility operations."""

    def __init__(self, db: AsyncSession):
        self.repo = FacilityRepository(db)

    async def get_by_id(self, facility_id: str) -> Facility:
        """Get a facility by ID or raise NotFoundError."""
        facility = await self.repo.get_by_id(facility_id)
        if facility is None:
            raise NotFoundError("Facility", facility_id)
        return facility

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
        """List facilities with filters and pagination."""
        return await self.repo.list(
            page=page,
            page_size=page_size,
            type=type,
            state=state,
            city=city,
            country=country,
        )
