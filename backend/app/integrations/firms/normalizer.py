"""
FIRMS CSV normalizer.

Parses raw FIRMS CSV text and converts each row into a dict that maps
directly to the Hotspot ORM model columns.

FIRMS data → Hotspot model mapping
──────────────────────────────────
latitude          → latitude
longitude         → longitude
bright_ti4 / brightness → brightness (Kelvin)
confidence (str/int)    → confidence (0-100 float)
acq_date + acq_time     → timestamp (UTC)
type (int)              → type (HotspotType string)
frp / brightness        → severity (derived)
id                      → "{source}-{lat:.4f}-{lon:.4f}-{acq_date}-{acq_time}"
geometry                → PostGIS POINT (derived from lat/lon)
country                 → "India" (hardcoded for India-wide ingestion)
status                  → "active" (all fresh detections are active)
"""
import csv
import hashlib
import io
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# VIIRS confidence letter codes → numeric (0-100)
# -------------------------------------------------------------------
_VIIRS_CONFIDENCE_MAP: Dict[str, float] = {
    "l": 30.0,   # low
    "n": 65.0,   # nominal
    "h": 90.0,   # high
}

# -------------------------------------------------------------------
# FIRMS type integer → mapped string
# -------------------------------------------------------------------
_FIRMS_TYPE_MAP: Dict[int, str] = {
    0: "unknown",
    2: "unknown",
    3: "unknown",
}


def classify_india_hotspot(lat: float, lon: float, brightness: float, confidence: float, type_col: Any = None) -> str:
    """
    Classifies raw NASA FIRMS thermal anomaly observations.

    The raw satellite 'type' is no longer mapped into the production ML taxonomy.
    Always returns 'unknown'. Classification into specific categories is deferred
    to Phase 6 ML pipeline.
    """
    return "unknown"


def _derive_severity(brightness: float, confidence: float) -> str:
    """
    Derive a severity label from brightness temperature and confidence.
    """
    score = brightness * 0.7 + confidence * 3.0
    if score >= 340 * 0.7 + 85 * 3.0:   # ≥ 493
        return "critical"
    if score >= 320 * 0.7 + 70 * 3.0:   # ≥ 434
        return "high"
    if score >= 295 * 0.7 + 50 * 3.0:   # ≥ 356.5
        return "medium"
    return "low"


def is_inside_india(lat: float, lon: float) -> bool:
    """
    Geographic boundary filter for Indian States and Union Territories.
    Filters out observations that fall outside India's landmass & UTs.
    """
    # 1. Bounding box check for India & UTs
    if not (6.0 <= lat <= 37.1 and 68.0 <= lon <= 97.4):
        return False
    # 2. Reject Sri Lanka (south of 10.0°N and east of 79.5°E)
    if lat < 10.0 and lon > 79.5:
        return False
    # 3. Reject Pakistan (west of Indian border)
    if lon < 68.1:
        return False
    if lat < 24.0 and lon < 68.1:
        return False
    if 24.0 <= lat < 28.0 and lon < 70.0:
        return False
    if 28.0 <= lat < 30.5 and lon < 73.5:
        return False
    if 30.5 <= lat < 32.5 and lon < 74.55:
        return False
    if lat >= 32.5 and lon < 73.8:
        return False
    # 4. Reject Nepal
    if 27.3 <= lat <= 30.5 and 80.0 <= lon <= 88.2:
        return False
    # 5. Reject Bangladesh
    if 20.6 < lat < 26.6 and 88.0 < lon < 92.6:
        is_wb = (lon <= 88.8) or (lat <= 21.8)
        is_tripura = (22.8 <= lat <= 24.6) and (91.1 <= lon <= 92.4)
        is_meghalaya = (25.0 <= lat <= 26.1) and (89.8 <= lon <= 92.8)
        is_assam = (lat >= 25.8)
        if not (is_wb or is_tripura or is_meghalaya or is_assam):
            return False
    # 6. Reject Myanmar
    if lon > 97.4:
        return False
    if lat < 22.0 and lon > 93.0:
        is_an = (6.5 <= lat <= 14.0) and (92.0 <= lon <= 94.5)
        if not is_an:
            return False
    return True


def _make_stable_id(source: str, lat: float, lon: float, acq_date: str, acq_time: str) -> str:
    """Generate a stable, idempotent ID for a FIRMS observation."""
    key = f"{source}|{lat:.4f}|{lon:.4f}|{acq_date}|{acq_time}"
    digest = hashlib.sha256(key.encode()).hexdigest()[:16]
    return f"FIRMS-{digest}"


def _parse_acq_datetime(acq_date: str, acq_time: str) -> datetime:
    """Parse FIRMS acquisition date/time into a UTC-aware datetime."""
    acq_time_padded = acq_time.zfill(4)
    dt_str = f"{acq_date} {acq_time_padded[:2]}:{acq_time_padded[2:]}:00"
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def _normalize_viirs_row(row: Dict[str, str], source: str) -> Dict[str, Any] | None:
    """Normalize a single VIIRS CSV row dict into a Hotspot-compatible dict."""
    try:
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        brightness = float(row.get("bright_ti4") or row.get("bright_412") or 0)
        acq_date = row["acq_date"].strip()
        acq_time = row["acq_time"].strip()
        confidence_raw = row.get("confidence", "n").strip().lower()
        try:
            confidence = float(confidence_raw)
        except ValueError:
            confidence = _VIIRS_CONFIDENCE_MAP.get(confidence_raw, 65.0)

        type_col = row.get("type")
        type_val = classify_india_hotspot(lat, lon, brightness, confidence, type_col)

        frp_raw = row.get("frp")
        frp_val = float(frp_raw) if frp_raw else None
    except (KeyError, ValueError) as exc:
        logger.debug("Skipping VIIRS row (parse error): %s — row: %s", exc, row)
        return None

    if not is_inside_india(lat, lon):
        return None

    if brightness <= 0:
        return None

    return {
        "id": _make_stable_id(source, lat, lon, acq_date, acq_time),
        "latitude": lat,
        "longitude": lon,
        "brightness": brightness,
        "confidence": confidence,
        "type": type_val,
        "severity": _derive_severity(brightness, confidence),
        "timestamp": _parse_acq_datetime(acq_date, acq_time),
        "facility_id": None,
        "status": "active",
        "country": "India",
        "state": None,
        "city": None,
        "district": None,
        "source": source,
        "frp": frp_val,
    }


def _normalize_modis_row(row: Dict[str, str], source: str) -> Dict[str, Any] | None:
    """Normalize a single MODIS CSV row dict into a Hotspot-compatible dict."""
    try:
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        brightness = float(row.get("brightness") or 0)
        acq_date = row["acq_date"].strip()
        acq_time = row["acq_time"].strip()
        confidence = float(row.get("confidence", "50"))

        type_col = row.get("type")
        type_val = classify_india_hotspot(lat, lon, brightness, confidence, type_col)

        frp_raw = row.get("frp")
        frp_val = float(frp_raw) if frp_raw else None
    except (KeyError, ValueError) as exc:
        logger.debug("Skipping MODIS row (parse error): %s — row: %s", exc, row)
        return None

    if not is_inside_india(lat, lon):
        return None

    if brightness <= 0:
        return None

    return {
        "id": _make_stable_id(source, lat, lon, acq_date, acq_time),
        "latitude": lat,
        "longitude": lon,
        "brightness": brightness,
        "confidence": min(float(confidence), 100.0),
        "type": type_val,
        "severity": _derive_severity(brightness, confidence),
        "timestamp": _parse_acq_datetime(acq_date, acq_time),
        "facility_id": None,
        "status": "active",
        "country": "India",
        "state": None,
        "city": None,
        "district": None,
        "source": source,
        "frp": frp_val,
    }


_NORMALIZER_MAP = {
    "VIIRS": _normalize_viirs_row,
    "MODIS": _normalize_modis_row,
}


def parse_firms_csv(csv_text: str, source: str) -> List[Dict[str, Any]]:
    """Parse FIRMS CSV text into a list of Hotspot-compatible dicts."""
    records: List[Dict[str, Any]] = []

    if not csv_text or not csv_text.strip():
        return records

    first_line = csv_text.strip().split("\n")[0]
    if first_line.startswith("{") or "error" in first_line.lower():
        logger.warning("FIRMS returned a non-CSV response: %s", first_line[:200])
        return records

    reader = csv.DictReader(io.StringIO(csv_text))
    normalizer = None
    for prefix, fn in _NORMALIZER_MAP.items():
        if source.startswith(prefix):
            normalizer = fn
            break

    if normalizer is None:
        normalizer = _normalize_viirs_row

    skipped = 0
    for row in reader:
        normalized = normalizer(row, source)
        if normalized is None:
            skipped += 1
            continue
        records.append(normalized)

    logger.info(
        "FIRMS parse: source=%s total=%d skipped=%d",
        source,
        len(records) + skipped,
        skipped,
    )
    return records
