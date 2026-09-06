"""
Hotspot Pydantic schemas.
Serialization matches the frontend Hotspot TypeScript interface exactly,
including camelCase field names (facilityId, not facility_id).
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


HotspotType = Literal[
    "industrial_thermal_source", "mining_thermal_source", "natural_fire", "unknown"
]
Severity = Literal["low", "medium", "high", "critical"]
HotspotStatus = Literal["active", "resolved", "monitoring"]


class HotspotResponse(BaseModel):
    """API response schema matching the frontend Hotspot interface."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    latitude: float
    longitude: float
    type: HotspotType  # Raw FIRMS type (e.g. 'unknown')
    brightness: float
    confidence: float
    severity: Severity
    timestamp: datetime
    facility_id: Optional[str] = Field(None, alias="facilityId", serialization_alias="facilityId")
    status: HotspotStatus

    # Phase 6 ML Prediction fields
    ml_type: Optional[HotspotType] = Field(None, alias="mlType", serialization_alias="mlType")
    ml_confidence: Optional[float] = Field(None, alias="mlConfidence", serialization_alias="mlConfidence")
    model_version: Optional[str] = Field(None, alias="modelVersion", serialization_alias="modelVersion")
    ml_explanation: Optional[str] = Field(None, alias="mlExplanation", serialization_alias="mlExplanation")

    # ESA WorldCover 10m land-cover context
    land_cover_class: Optional[int] = Field(None, alias="landCoverClass", serialization_alias="landCoverClass")
    land_cover_name: Optional[str] = Field(None, alias="landCoverName", serialization_alias="landCoverName")


class ActivityByType(BaseModel):
    industrial_thermal_source: int = Field(0, alias="industrialThermalSource", serialization_alias="industrialThermalSource")
    mining_thermal_source: int = Field(0, alias="miningThermalSource", serialization_alias="miningThermalSource")
    natural_fire: int = Field(0, alias="naturalFire", serialization_alias="naturalFire")
    unknown: int = 0
    
    model_config = ConfigDict(populate_by_name=True)


class ActivityDayResponse(BaseModel):
    date: str  # YYYY-MM-DD
    total: int
    unique_sources: int = Field(0, alias="uniqueSources", serialization_alias="uniqueSources")
    by_type: ActivityByType = Field(..., alias="byType", serialization_alias="byType")
    by_type_unique: ActivityByType = Field(..., alias="byTypeUnique", serialization_alias="byTypeUnique")
    
    model_config = ConfigDict(populate_by_name=True)


class ActivityResponse(BaseModel):
    days: list[ActivityDayResponse]
