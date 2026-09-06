"""
ThermalTrace ML Feature Extraction Engine.
Converts raw FIRMS satellite observations and spatial/temporal context into feature vectors.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import math


FEATURE_COLUMNS = [
    "bright_ti4",
    "bright_ti5",
    "brightness_ratio",
    "temp_diff",
    "frp",
    "frp_density",
    "confidence_norm",
    "is_day",
    "facility_dist_km",
    "persistence_count",
]


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate geodesic distance in km between two lat/lon points."""
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def extract_features(
    *,
    brightness: float,
    bright_ti5: Optional[float] = None,
    frp: Optional[float] = None,
    confidence: float,
    latitude: float,
    longitude: float,
    timestamp: Optional[datetime] = None,
    facility_dist_km: Optional[float] = None,
    persistence_count: Optional[int] = None,
) -> Dict[str, float]:
    """
    Extract ML feature vector from satellite observation data.
    """
    ti4 = float(brightness) if brightness else 300.0
    ti5 = float(bright_ti5) if bright_ti5 and bright_ti5 > 0 else (ti4 - 15.0)
    frp_val = float(frp) if frp and frp >= 0 else 5.0

    brightness_ratio = ti4 / (ti5 + 1e-5)
    temp_diff = ti4 - ti5
    frp_density = frp_val / (ti4 + 1e-5)
    confidence_norm = max(0.0, min(1.0, float(confidence) / 100.0))

    # Day/Night determination from timestamp hour if available
    is_day = 1.0
    if timestamp:
        hour = timestamp.hour
        is_day = 1.0 if 6 <= hour <= 18 else 0.0

    dist_km = float(facility_dist_km) if facility_dist_km is not None else 25.0
    p_count = float(persistence_count) if persistence_count is not None else 1.0

    return {
        "bright_ti4": ti4,
        "bright_ti5": ti5,
        "brightness_ratio": brightness_ratio,
        "temp_diff": temp_diff,
        "frp": frp_val,
        "frp_density": frp_density,
        "confidence_norm": confidence_norm,
        "is_day": is_day,
        "facility_dist_km": dist_km,
        "persistence_count": p_count,
    }


def features_to_vector(features_dict: Dict[str, float]) -> List[float]:
    """Convert feature dictionary to ordered feature vector for model input."""
    return [features_dict.get(col, 0.0) for col in FEATURE_COLUMNS]
