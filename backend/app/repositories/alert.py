"""
Alert repository — database access layer for alert queries.
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.alert import Alert

logger = logging.getLogger(__name__)


class AlertRepository:
    """Repository for alert database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, alert_id: str) -> Optional[Alert]:
        """Get a single alert by ID."""
        result = await self.db.execute(
            select(Alert).where(Alert.id == alert_id)
        )
        return result.scalar_one_or_none()

    async def get_by_hotspot_id(self, hotspot_id: str) -> Optional[Alert]:
        """Get an alert by associated hotspot ID for idempotency checks."""
        result = await self.db.execute(
            select(Alert).where(Alert.hotspot_id == hotspot_id)
        )
        return result.scalar_one_or_none()

    async def create(self, alert: Alert) -> Alert:
        """Create and persist a new alert record."""
        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)
        return alert

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 100,
        severity: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        date_str: Optional[str] = None,
    ) -> tuple[list[Alert], int]:
        """
        List alerts with optional filters and pagination.
        Filters by IST date when date_str is provided.
        Returns (items, total_count).
        """
        query = select(Alert)
        count_query = select(func.count()).select_from(Alert)

        if severity is not None:
            query = query.where(Alert.severity == severity)
            count_query = count_query.where(Alert.severity == severity)
        if acknowledged is not None:
            query = query.where(Alert.acknowledged == acknowledged)
            count_query = count_query.where(Alert.acknowledged == acknowledged)
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                ist_day = func.date_trunc("day", func.timezone("Asia/Kolkata", Alert.timestamp))
                query = query.where(ist_day == target_date)
                count_query = count_query.where(ist_day == target_date)
            except ValueError:
                pass

        # Order by timestamp descending (most recent first)
        query = query.order_by(Alert.timestamp.desc())

        # Pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return items, total
