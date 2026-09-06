"""
NASA FIRMS API client.

Fetches CSV-format active fire / thermal anomaly data from the FIRMS
VIIRS_SNPP_NRT and MODIS_NRT datasets for a given area-of-interest.

Endpoint reference:
  https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{source}/{area}/{days}

- source: VIIRS_SNPP_NRT  (primary, 375 m) or MODIS_NRT (1 km fallback)
- area:   west,south,east,north  (WGS-84 bounding box)
- days:   1-10 (number of past days to retrieve)

The client is intentionally thin — it only fetches and returns raw text.
All validation and transformation is done in normalizer.py.
"""
import logging

import httpx

logger = logging.getLogger(__name__)

# India-wide bounding box (west, south, east, north)
INDIA_BBOX = "68.0,6.0,98.0,38.0"

FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


class FIRMSClient:
    """Async HTTP client for the NASA FIRMS Area-of-Interest API."""

    def __init__(self, map_key: str, timeout_seconds: float = 30.0):
        if not map_key:
            raise ValueError("FIRMS_MAP_KEY is required but not set in .env")
        self._map_key = map_key
        self._timeout = timeout_seconds

    async def fetch_csv(
        self,
        source: str = "VIIRS_SNPP_NRT",
        bbox: str = INDIA_BBOX,
        days: int = 1,
    ) -> str:
        """
        Fetch raw CSV text from the FIRMS API.

        Args:
            source: FIRMS data source identifier (e.g. VIIRS_SNPP_NRT).
            bbox:   Bounding box string "west,south,east,north".
            days:   Number of past days (1–10).

        Returns:
            Raw CSV text (first line is the header).

        Raises:
            httpx.HTTPStatusError: On non-2xx response.
            httpx.RequestError:    On network / timeout errors.
        """
        days = max(1, min(days, 5))
        url = f"{FIRMS_BASE_URL}/{self._map_key}/{source}/{bbox}/{days}"
        logger.info("FIRMS fetch: source=%s bbox=%s days=%d", source, bbox, days)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url)
            response.raise_for_status()

        body = response.text
        line_count = body.count("\n")
        logger.info("FIRMS response: %d lines", line_count)
        return body
