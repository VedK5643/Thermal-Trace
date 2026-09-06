"""
Hotspot service — business logic layer.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.hotspot import Hotspot
from app.repositories.hotspot import HotspotRepository


class HotspotService:
    """Business logic for hotspot operations."""

    def __init__(self, db: AsyncSession):
        self.repo = HotspotRepository(db)

    async def get_by_id(self, hotspot_id: str) -> Hotspot:
        """Get a hotspot by ID or raise NotFoundError."""
        hotspot = await self.repo.get_by_id(hotspot_id)
        if hotspot is None:
            raise NotFoundError("Hotspot", hotspot_id)
        return hotspot

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 100,
        type: Optional[str] = None,
        min_confidence: Optional[float] = None,
        severity: Optional[str] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        country: Optional[str] = None,
        source: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        near_lat: Optional[float] = None,
        near_lng: Optional[float] = None,
        radius_km: Optional[float] = None,
    ) -> tuple[list[Hotspot], int]:
        """List hotspots with filters and pagination."""
        return await self.repo.list(
            page=page,
            page_size=page_size,
            type=type,
            min_confidence=min_confidence,
            severity=severity,
            state=state,
            city=city,
            country=country,
            source=source,
            start_date=start_date,
            end_date=end_date,
            near_lat=near_lat,
            near_lng=near_lng,
            radius_km=radius_km,
        )

    async def get_activity(
        self,
        *,
        end_date: datetime,
        min_confidence: Optional[float] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        country: Optional[str] = None,
        source: Optional[str] = None,
    ) -> dict:
        """Get 7-day activity ending on end_date."""
        from datetime import timedelta
        # Compute start date (midnight 6 days prior to cover full 7-day range)
        start_date = (end_date - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        rows = await self.repo.get_activity(
            min_confidence=min_confidence,
            state=state,
            city=city,
            country=country,
            source=source,
            start_date=start_date,
            end_date=end_date,
        )

        # Initialize 7 empty days
        days = []
        for i in range(7):
            day_dt = start_date + timedelta(days=i)
            day_str = day_dt.strftime("%Y-%m-%d")
            days.append({
                "date": day_str,
                "total": 0,
                "unique_sources": 0,
                "by_type": {
                    "industrial_thermal_source": 0,
                    "mining_thermal_source": 0,
                    "natural_fire": 0,
                    "unknown": 0,
                },
                "by_type_unique": {
                    "industrial_thermal_source": 0,
                    "mining_thermal_source": 0,
                    "natural_fire": 0,
                    "unknown": 0,
                }
            })
            
        day_map = {d["date"]: d for d in days}
        
        # Fill in data
        for row in rows:
            day_dt = row["day"]
            if not day_dt:
                continue
            day_str = day_dt.strftime("%Y-%m-%d")
            if day_str in day_map:
                count = row["count"]
                unique_count = row["unique_source_count"]
                type_ = row["type"]
                day_map[day_str]["by_type"][type_] = count
                day_map[day_str]["total"] += count
                day_map[day_str]["by_type_unique"][type_] = unique_count
                day_map[day_str]["unique_sources"] += unique_count
                
        return {"days": days}
