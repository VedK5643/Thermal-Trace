"""
FIRMS raw record schemas.

These are the raw CSV column definitions for each supported FIRMS source.
Only the columns we actually use are modelled; extra columns are ignored.

Reference column lists:
  VIIRS_SNPP_NRT:
    latitude, longitude, bright_ti4, scan, track, acq_date, acq_time,
    satellite, instrument, confidence, version, bright_ti5, frp, daynight, type

  MODIS_NRT:
    latitude, longitude, brightness, scan, track, acq_date, acq_time,
    satellite, instrument, confidence, version, bright_t31, frp, daynight, type
"""
from datetime import date, time
from typing import Optional

from pydantic import BaseModel, Field


class FIRMSVIIRSRecord(BaseModel):
    """
    VIIRS SNPP / NOAA-20 NRT active fire record.
    Source: VIIRS_SNPP_NRT, VIIRS_NOAA20_NRT
    """

    latitude: float
    longitude: float
    bright_ti4: float = Field(..., description="Brightness temperature channel I4 (Kelvin)")
    acq_date: date = Field(..., description="Acquisition date YYYY-MM-DD")
    acq_time: str = Field(..., description="Acquisition time HHMM UTC")
    confidence: str = Field(
        ...,
        description="Confidence: 'l' (low), 'n' (nominal), 'h' (high) for VIIRS",
    )
    frp: Optional[float] = Field(None, description="Fire Radiative Power (MW)")
    type: Optional[int] = Field(
        None, description="0=presumed vegetation fire, 2=offshore, 3=other static source"
    )


class FIRMSMODISRecord(BaseModel):
    """
    MODIS NRT active fire record.
    Source: MODIS_NRT
    """

    latitude: float
    longitude: float
    brightness: float = Field(..., description="Brightness temperature band 21/22 (Kelvin)")
    acq_date: date = Field(..., description="Acquisition date YYYY-MM-DD")
    acq_time: str = Field(..., description="Acquisition time HHMM UTC")
    confidence: int = Field(..., ge=0, le=100, description="Detection confidence 0-100")
    frp: Optional[float] = Field(None, description="Fire Radiative Power (MW)")
    type: Optional[int] = Field(None, description="0=vegetation, 2=offshore, 3=other")
