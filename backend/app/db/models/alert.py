"""
Alert database model.
Matches the frontend Alert TypeScript interface.
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String

from app.db.base import Base


class Alert(Base):
    """System alert/notification record."""

    __tablename__ = "alerts"

    id = Column(String, primary_key=True)
    hotspot_id = Column(String, ForeignKey("hotspots.id"), nullable=True)
    facility_id = Column(String, ForeignKey("facilities.id"), nullable=True)
    severity = Column(String, nullable=False)  # info | warning | critical
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    acknowledged = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_alerts_severity", "severity"),
        Index("ix_alerts_timestamp", "timestamp"),
        Index("ix_alerts_hotspot_id", "hotspot_id"),
        Index("ix_alerts_facility_id", "facility_id"),
    )
