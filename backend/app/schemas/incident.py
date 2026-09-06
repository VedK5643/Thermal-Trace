"""
Incident Pydantic schemas.
Matches the frontend Incident TypeScript interface.
Incidents are derived from hotspot+facility join (no separate DB table).
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


HotspotType = Literal[
    "industrial_thermal_source", "mining_thermal_source", "natural_fire", "unknown"
]
Severity = Literal["low", "medium", "high", "critical"]
HotspotStatus = Literal["active", "resolved", "monitoring"]


class IncidentResponse(BaseModel):
    """API response schema matching the frontend Incident interface."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    hotspot_id: str = Field(alias="hotspotId", serialization_alias="hotspotId")
    facility_id: Optional[str] = Field(None, alias="facilityId", serialization_alias="facilityId")
    facility_name: Optional[str] = Field(None, alias="facilityName", serialization_alias="facilityName")
    type: HotspotType
    latitude: float
    longitude: float
    brightness: float
    confidence: float
    severity: Severity
    timestamp: datetime
    status: HotspotStatus
