"""
Facility Pydantic schemas.
Matches the frontend Facility TypeScript interface.
"""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


FacilityType = str


class FacilityResponse(BaseModel):
    """API response schema matching the frontend Facility interface."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: Optional[str] = "Unknown Facility"
    type: FacilityType
    rawType: Optional[str] = None
    latitude: float
    longitude: float
    city: Optional[str] = "Unknown"
    state: Optional[str] = "Unknown"
    country: Optional[str] = "India"
    source: Optional[str] = "osm"
    osm_type: Optional[str] = None
    osm_id: Optional[int] = None
    raw_tags: Optional[dict] = None
