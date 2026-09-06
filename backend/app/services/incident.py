"""
Incident service — derives incidents from hotspot+facility join.
Mirrors the frontend's deriveIncidents() utility (src/utils/incidents.ts).
No separate incidents database table.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.hotspot import Hotspot
from app.db.models.facility import Facility


class IncidentService:
    """
    Business logic for incident operations.
    Incidents are derived server-side from hotspot + facility joins.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, incident_id: str) -> dict:
        """
        Get a single incident (derived from hotspot + facility).
        The incident ID is the hotspot ID.
        """
        query = (
            select(
                Hotspot.id,
                Hotspot.id.label("hotspot_id"),
                Hotspot.latitude,
                Hotspot.longitude,
                Hotspot.type,
                Hotspot.brightness,
                Hotspot.confidence,
                Hotspot.severity,
                Hotspot.timestamp,
                Hotspot.status,
                Hotspot.facility_id,
                Facility.name.label("facility_name"),
            )
            .outerjoin(Facility, Hotspot.facility_id == Facility.id)
            .where(Hotspot.id == incident_id)
        )

        result = await self.db.execute(query)
        row = result.one_or_none()

        if row is None:
            raise NotFoundError("Incident", incident_id)

        return self._row_to_dict(row)

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 100,
        type: Optional[str] = None,
        severity: Optional[str] = None,
        min_confidence: Optional[float] = None,
        state: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> tuple[list[dict], int]:
        """
        List incidents (derived from hotspots + facilities) with filters.
        Returns (items, total_count).
        """
        base_query = (
            select(
                Hotspot.id,
                Hotspot.id.label("hotspot_id"),
                Hotspot.latitude,
                Hotspot.longitude,
                Hotspot.type,
                Hotspot.brightness,
                Hotspot.confidence,
                Hotspot.severity,
                Hotspot.timestamp,
                Hotspot.status,
                Hotspot.facility_id,
                Facility.name.label("facility_name"),
            )
            .outerjoin(Facility, Hotspot.facility_id == Facility.id)
        )

        count_query = select(func.count()).select_from(Hotspot)

        # Apply filters
        if type is not None:
            base_query = base_query.where(Hotspot.type == type)
            count_query = count_query.where(Hotspot.type == type)
        if severity is not None:
            base_query = base_query.where(Hotspot.severity == severity)
            count_query = count_query.where(Hotspot.severity == severity)
        if min_confidence is not None:
            base_query = base_query.where(Hotspot.confidence >= min_confidence)
            count_query = count_query.where(Hotspot.confidence >= min_confidence)
        if state is not None:
            base_query = base_query.where(Hotspot.state == state)
            count_query = count_query.where(Hotspot.state == state)
        if start_date is not None:
            base_query = base_query.where(Hotspot.timestamp >= start_date)
            count_query = count_query.where(Hotspot.timestamp >= start_date)
        if end_date is not None:
            base_query = base_query.where(Hotspot.timestamp <= end_date)
            count_query = count_query.where(Hotspot.timestamp <= end_date)

        # Order by timestamp descending
        base_query = base_query.order_by(Hotspot.timestamp.desc())

        # Pagination
        offset = (page - 1) * page_size
        base_query = base_query.offset(offset).limit(page_size)

        # Execute
        result = await self.db.execute(base_query)
        rows = result.all()
        items = [self._row_to_dict(row) for row in rows]

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return items, total

    @staticmethod
    def _row_to_dict(row) -> dict:
        """Convert a database row to an incident dictionary."""
        facility_name = row.facility_name
        if facility_name is None and row.facility_id is not None:
            facility_name = "Unknown Facility"
        elif facility_name is None:
            facility_name = None

        return {
            "id": row.id,
            "hotspot_id": row.hotspot_id,
            "facility_id": row.facility_id,
            "facility_name": facility_name,
            "type": row.type,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "brightness": row.brightness,
            "confidence": row.confidence,
            "severity": row.severity,
            "timestamp": row.timestamp,
            "status": row.status,
        }
