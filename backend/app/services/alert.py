"""
Alert service — business logic layer.
"""
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.alert import Alert
from app.repositories.alert import AlertRepository


class AlertService:
    """Business logic for alert operations."""

    def __init__(self, db: AsyncSession):
        self.repo = AlertRepository(db)

    async def get_by_id(self, alert_id: str) -> Alert:
        """Get an alert by ID or raise NotFoundError."""
        alert = await self.repo.get_by_id(alert_id)
        if alert is None:
            raise NotFoundError("Alert", alert_id)
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
        """List alerts with filters and pagination."""
        return await self.repo.list(
            page=page,
            page_size=page_size,
            severity=severity,
            acknowledged=acknowledged,
            date_str=date_str,
        )

    async def evaluate_hotspot_alert(self, hotspot: Any) -> Optional[Alert]:
        """
        Evaluates a hotspot observation and generates an alert if multi-factor conditions warrant it.
        Idempotently checks if an alert already exists for hotspot.id.
        Multi-factor reasoning: ML prediction, ML confidence, FRP, facility distance, persistence count.
        """
        existing = await self.repo.get_by_hotspot_id(hotspot.id)
        if existing:
            return None

        ml_type = getattr(hotspot, "ml_type", None)
        ml_conf = getattr(hotspot, "ml_confidence", 0.0) or 0.0
        frp = getattr(hotspot, "frp", 0.0) or 0.0
        dist = getattr(hotspot, "facility_dist_km", 999.0) or 999.0
        pers = getattr(hotspot, "persistence_count", 0) or 0

        # Multi-factor severity evaluation logic
        if ml_type == "industrial_thermal_source" and ml_conf >= 0.75 and frp >= 20.0 and dist <= 5.0:
            severity = "critical"
            title = "Critical Industrial Thermal Event near Facility"
            msg = f"Predicted {ml_type.replace('_', ' ')} detected with {ml_conf*100:.1f}% model probability, FRP {frp:.1f} MW near facility ({dist:.1f} km)."
        elif ml_type == "industrial_thermal_source" and ml_conf >= 0.60:
            severity = "high"
            title = "High Confidence Industrial Event"
            msg = f"Predicted {ml_type.replace('_', ' ')} detected ({ml_conf*100:.1f}% ML confidence, FRP {frp:.1f} MW)."
        elif ml_conf >= 0.50 or pers >= 3:
            severity = "medium"
            title = f"MEDIUM: Persistent Thermal Anomaly"
            msg = f"Thermal anomaly exhibiting persistence ({pers} detections) with {ml_conf*100:.1f}% ML confidence."
        else:
            severity = "low"
            title = "LOW: Thermal Observation"
            msg = f"NASA FIRMS thermal observation recorded."

        if severity in ("medium", "high", "critical"):
            alert = Alert(
                id=f"ALERT-{hotspot.id}",
                hotspot_id=hotspot.id,
                facility_id=getattr(hotspot, "facility_id", None),
                severity=severity,
                title=title,
                message=msg,
                timestamp=hotspot.timestamp,
                acknowledged=False,
            )
            return await self.repo.create(alert)

        return None
