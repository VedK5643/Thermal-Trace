"""
ESA WorldCover 10m Land-Cover Lookup Service.

Provides deterministic land-cover classification for any lat/lon coordinate
using the ESA WorldCover 2021 v200 dataset (CC-BY 4.0).

Architecture:
    - Remote Cloud-Optimized GeoTIFF (COG) streaming from AWS S3
    - LRU tile caching for batch performance
    - Graceful fallback to (0, "Unknown") on errors

Data source:
    ESA WorldCover 2021 v200 (10m resolution, 11 FAO-LCCS classes)
    https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/
"""
import logging
import math
from functools import lru_cache
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# ─── ESA WorldCover 2021 v200 Class Definitions ─────────────────────────
ESA_WORLDCOVER_CLASSES: dict[int, str] = {
    10: "Tree Cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare / Sparse Vegetation",
    70: "Snow and Ice",
    80: "Permanent Water Bodies",
    90: "Herbaceous Wetland",
    95: "Mangroves",
    100: "Moss and Lichen",
}

# Colors for frontend display (hex)
ESA_WORLDCOVER_COLORS: dict[int, str] = {
    10: "#006400",   # Dark green - tree cover
    20: "#FFBB22",   # Orange - shrubland
    30: "#FFFF4C",   # Yellow - grassland
    40: "#F096FF",   # Pink - cropland
    50: "#FA0000",   # Red - built-up
    60: "#B4B4B4",   # Gray - bare
    70: "#F0F0F0",   # White - snow
    80: "#0064C8",   # Blue - water
    90: "#0096A0",   # Teal - wetland
    95: "#00CF75",   # Green - mangroves
    100: "#FAE6A0",  # Light yellow - moss
}

# AWS S3 public URL template (no authentication needed)
_ESA_COG_URL_TEMPLATE = (
    "https://esa-worldcover.s3.eu-central-1.amazonaws.com/"
    "v200/2021/map/ESA_WorldCover_10m_2021_v200_{tile_id}_Map.tif"
)


def _get_tile_id(lat: float, lon: float) -> str:
    """Calculate the 3×3 degree lower-left tile name for ESA WorldCover."""
    lat_ll = int(math.floor(lat / 3.0) * 3)
    lon_ll = int(math.floor(lon / 3.0) * 3)
    lat_str = f"N{lat_ll:02d}" if lat_ll >= 0 else f"S{abs(lat_ll):02d}"
    lon_str = f"E{lon_ll:03d}" if lon_ll >= 0 else f"W{abs(lon_ll):03d}"
    return f"{lat_str}{lon_str}"


def _sample_cog_point(url: str, lon: float, lat: float) -> Optional[int]:
    """
    Sample a single (lon, lat) from a remote Cloud-Optimized GeoTIFF.
    Uses HTTP range requests — only downloads the needed bytes.
    """
    try:
        import rasterio
        from rasterio.errors import RasterioIOError

        env_opts = {
            "AWS_NO_SIGN_REQUEST": "YES",
            "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
            "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
            "GDAL_HTTP_TIMEOUT": "10",
            "GDAL_HTTP_MAX_RETRY": "2",
        }
        with rasterio.Env(**env_opts):
            with rasterio.open(url) as src:
                vals = list(src.sample([(lon, lat)]))
                if vals and len(vals[0]) > 0:
                    return int(vals[0][0])
        return None
    except ImportError:
        logger.warning("rasterio not installed — land-cover lookup unavailable")
        return None
    except Exception as e:
        logger.warning("ESA WorldCover COG sampling failed for (%s, %s): %s", lat, lon, e)
        return None


def get_land_cover(lat: float, lon: float) -> Tuple[Optional[int], str]:
    """
    Look up ESA WorldCover 10m land-cover class for a coordinate.

    Args:
        lat: Latitude (WGS84)
        lon: Longitude (WGS84)

    Returns:
        Tuple of (class_id, class_name).
        Returns (None, "Unknown") on error or if rasterio is unavailable.
    """
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None, "Unknown"

    tile_id = _get_tile_id(lat, lon)
    url = _ESA_COG_URL_TEMPLATE.format(tile_id=tile_id)

    class_id = _sample_cog_point(url, lon, lat)

    if class_id is None or class_id == 0:
        return None, "Unknown"

    class_name = ESA_WORLDCOVER_CLASSES.get(class_id, "Unknown")
    return class_id, class_name


def get_land_cover_batch(
    coordinates: list[Tuple[float, float]],
) -> list[Tuple[Optional[int], str]]:
    """
    Batch land-cover lookup — groups coordinates by ESA tile for efficiency.

    Args:
        coordinates: List of (lat, lon) tuples.

    Returns:
        List of (class_id, class_name) tuples in same order as input.
    """
    try:
        import rasterio
    except ImportError:
        logger.warning("rasterio not installed — batch land-cover lookup unavailable")
        return [(None, "Unknown")] * len(coordinates)

    from collections import defaultdict

    # Group by tile
    tile_groups: dict[str, list[Tuple[int, float, float]]] = defaultdict(list)
    for idx, (lat, lon) in enumerate(coordinates):
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            tile_id = _get_tile_id(lat, lon)
            tile_groups[tile_id].append((idx, lon, lat))

    results: list[Tuple[Optional[int], str]] = [(None, "Unknown")] * len(coordinates)

    env_opts = {
        "AWS_NO_SIGN_REQUEST": "YES",
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
        "GDAL_HTTP_TIMEOUT": "15",
        "GDAL_HTTP_MAX_RETRY": "2",
    }

    with rasterio.Env(**env_opts):
        for tile_id, points in tile_groups.items():
            url = _ESA_COG_URL_TEMPLATE.format(tile_id=tile_id)
            coords_for_sample = [(lon, lat) for _, lon, lat in points]
            try:
                with rasterio.open(url) as src:
                    sampled = list(src.sample(coords_for_sample))
                for (orig_idx, _, _), val in zip(points, sampled):
                    class_id = int(val[0]) if val is not None and len(val) > 0 else None
                    if class_id and class_id != 0:
                        class_name = ESA_WORLDCOVER_CLASSES.get(class_id, "Unknown")
                        results[orig_idx] = (class_id, class_name)
            except Exception as e:
                logger.warning("Batch COG sampling failed for tile %s: %s", tile_id, e)

    return results


def get_class_name(class_id: Optional[int]) -> str:
    """Get human-readable class name from ESA WorldCover class ID."""
    if class_id is None:
        return "Unknown"
    return ESA_WORLDCOVER_CLASSES.get(class_id, "Unknown")


def get_class_color(class_id: Optional[int]) -> str:
    """Get hex color for ESA WorldCover class ID."""
    if class_id is None:
        return "#6B7280"
    return ESA_WORLDCOVER_COLORS.get(class_id, "#6B7280")
