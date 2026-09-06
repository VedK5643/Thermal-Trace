"""
Alert Pydantic schemas.
Matches the frontend Alert TypeScript interface with camelCase aliases.
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


AlertSeverity = Literal["info", "low", "medium", "high", "warning", "critical"]


class AlertResponse(BaseModel):
    """API response schema matching the frontend Alert interface."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    hotspot_id: Optional[str] = Field(None, alias="hotspotId", serialization_alias="hotspotId")
    facility_id: Optional[str] = Field(None, alias="facilityId", serialization_alias="facilityId")
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime
    acknowledged: bool
