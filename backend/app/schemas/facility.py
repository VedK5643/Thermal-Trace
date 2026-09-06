"""
Facility Pydantic schemas.
Matches the frontend Facility TypeScript interface.
"""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


FacilityType = Literal[
    "refinery", "power_plant", "steel_plant", "cement_plant", "lng_terminal"
]


class FacilityResponse(BaseModel):
    """API response schema matching the frontend Facility interface."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    type: FacilityType
    latitude: float
    longitude: float
    city: str
    state: str
    country: str
    source: Optional[str] = "unknown"
