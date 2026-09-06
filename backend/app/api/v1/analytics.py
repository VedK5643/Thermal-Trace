import json
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models.hotspot import Hotspot
from app.db.models.alert import Alert
from app.core.redis import redis_manager
from app.core.config import settings

router = APIRouter()


@router.get("/analytics/summary")
async def get_analytics_summary(
    state: Optional[str] = Query(None),
    classification: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """
    Get top-level aggregated counts, classification distribution, alert statistics, and persistent anomaly metrics.
    Uses Redis canonical response caching with 300s TTL.
    """
    canonical_key = f"analytics:summary:state={state or 'all'}:class={classification or 'all'}:sev={severity or 'all'}:days={days}"
    cached_payload = await redis_manager.get_cache(canonical_key)
    if cached_payload:
        try:
            return json.loads(cached_payload)
        except Exception:
            pass

    stmt = select(Hotspot)
    if state:
        stmt = stmt.where(Hotspot.state == state)
    if classification:
        stmt = stmt.where(Hotspot.ml_type == classification)
    if severity:
        stmt = stmt.where(Hotspot.severity == severity)

    res = await db.execute(stmt)
    hotspots = res.scalars().all()

    total_obs = len(hotspots)
    unique_sources_seen = set()
    class_counts: Dict[str, int] = {
        "industrial_thermal_source": 0,
        "mining_thermal_source": 0,
        "natural_fire": 0,
        "unknown": 0,
    }
    sev_counts: Dict[str, int] = {}
    high_frp_count = 0
    persistent_count = 0
    anomalous_count = 0

    for h in hotspots:
        source_id = f"{round(h.latitude, 3)}_{round(h.longitude, 3)}"
        is_new_source = source_id not in unique_sources_seen
        if is_new_source:
            unique_sources_seen.add(source_id)

        ml_t = getattr(h, "ml_type", "unknown") or "unknown"
        if is_new_source:
            class_counts[ml_t] = class_counts.get(ml_t, 0) + 1

        sev = h.severity or "medium"
        sev_counts[sev] = sev_counts.get(sev, 0) + 1

        if getattr(h, "frp", None) and h.frp >= 35.0:
            high_frp_count += 1
        if getattr(h, "persistence_count", 0) >= 3:
            persistent_count += 1
        if (getattr(h, "frp", 0) and h.frp >= 35.0) or getattr(h, "persistence_count", 0) >= 3:
            anomalous_count += 1

    total_unique = len(unique_sources_seen)
    industrial_total = class_counts["industrial_thermal_source"]
    industrial_pct = round((industrial_total / total_unique * 100), 1) if total_unique > 0 else 0.0

    # Query active alert counts
    alert_stmt = select(func.count()).select_from(Alert).where(Alert.severity.in_(["high", "critical"]))
    alert_res = await db.execute(alert_stmt)
    high_critical_alerts = alert_res.scalar() or 0

    payload = {
        "totalObservations": total_obs,
        "uniqueSources": total_unique,
        "classificationDistribution": class_counts,
        "severityDistribution": sev_counts,
        "industrialSourcePercentage": industrial_pct,
        "highCriticalAlerts": high_critical_alerts,
        "persistentEvents": persistent_count,
        "highFrpEvents": high_frp_count,
        "anomalousEvents": anomalous_count,
        "modelVersion": "thermalwatch-v1",
        "benchmarkDisclosure": "Validated 4-class taxonomy. OpenStreetMap industrial infrastructure and ESA WorldCover land-use data provide corroborating geospatial evidence for spatial classification context.",
        "psCategoryCoverage": {
            "industrial_fires": {
                "psCategory": "Industrial Fires / Heat",
                "modelClass": "industrial_thermal_source",
                "coverageType": "classified",
                "description": "High temporal persistence (≥9 months/yr incl. monsoon) & OSM industrial proximity (≤2 km)"
            },
            "gas_flares": {
                "psCategory": "Gas Flares",
                "modelClass": "industrial_thermal_source",
                "coverageType": "grouped",
                "description": "Subsumed under industrial process heat; persistent flaring at oil refineries & petrochemical complexes"
            },
            "mining_activity": {
                "psCategory": "Mining Activity",
                "modelClass": "mining_thermal_source",
                "coverageType": "classified",
                "description": "High temporal persistence & spatial proximity (≤2 km) to OSM quarry features"
            },
            "agricultural_burning": {
                "psCategory": "Agricultural Burning",
                "modelClass": "natural_fire",
                "coverageType": "grouped",
                "description": "Seasonal non-industrial open fires in agricultural zones (crop residue / stubble burning)"
            },
            "wildfire_forest_fire": {
                "psCategory": "Wildfire / Forest Fire",
                "modelClass": "natural_fire",
                "coverageType": "grouped",
                "description": "Seasonal non-industrial open vegetation fires in forested & woodland regions"
            },
            "other_natural_fires": {
                "psCategory": "Other Natural Fires",
                "modelClass": "natural_fire",
                "coverageType": "grouped",
                "description": "Seasonal open fires across grasslands, shrublands, and non-crop vegetation"
            }
        }
    }

    await redis_manager.set_cache(canonical_key, json.dumps(payload), ttl_seconds=settings.analytics_cache_ttl_seconds)
    return payload


@router.get("/analytics/temporal")
async def get_temporal_analytics(
    state: Optional[str] = Query(None),
    classification: Optional[str] = Query(None),
    interval: str = Query("day", pattern="^(day|week)$"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get time-series observation trends aggregated by date and ML classification.
    Uses Redis canonical response caching with 300s TTL.
    """
    canonical_key = f"analytics:temporal:state={state or 'all'}:class={classification or 'all'}:interval={interval}"
    cached_payload = await redis_manager.get_cache(canonical_key)
    if cached_payload:
        try:
            return json.loads(cached_payload)
        except Exception:
            pass

    stmt = select(Hotspot)
    if state:
        stmt = stmt.where(Hotspot.state == state)
    if classification:
        stmt = stmt.where(Hotspot.ml_type == classification)

    res = await db.execute(stmt)
    hotspots = res.scalars().all()

    buckets: Dict[str, Dict[str, int]] = {}
    for h in hotspots:
        if not h.timestamp:
            continue
        date_str = h.timestamp.strftime("%Y-%m-%d")
        if date_str not in buckets:
            buckets[date_str] = {
                "industrial_thermal_source": 0,
                "mining_thermal_source": 0,
                "natural_fire": 0,
                "unknown": 0,
                "total": 0,
            }
        ml_t = getattr(h, "ml_type", "unknown") or "unknown"
        buckets[date_str][ml_t] = buckets[date_str].get(ml_t, 0) + 1
        buckets[date_str]["total"] += 1

    series = []
    for date_key in sorted(buckets.keys()):
        item = {"date": date_key, **buckets[date_key]}
        series.append(item)

    payload = {
        "interval": interval,
        "totalDataPoints": len(series),
        "series": series
    }

    await redis_manager.set_cache(canonical_key, json.dumps(payload), ttl_seconds=settings.analytics_cache_ttl_seconds)
    return payload


@router.get("/analytics/regional")
async def get_regional_analytics(
    db: AsyncSession = Depends(get_db),
):
    """
    Get state-level aggregation of total observations, industrial thermal source predictions, active alerts, and persistent events across India.
    Uses Redis canonical response caching with 300s TTL.
    """
    canonical_key = "analytics:regional:all"
    cached_payload = await redis_manager.get_cache(canonical_key)
    if cached_payload:
        try:
            return json.loads(cached_payload)
        except Exception:
            pass

    stmt = select(Hotspot)
    res = await db.execute(stmt)
    hotspots = res.scalars().all()

    states: Dict[str, Dict[str, int]] = {}
    for h in hotspots:
        st = getattr(h, "state", None) or "Unknown State"
        if st not in states:
            states[st] = {
                "totalObservations": 0,
                "industrialObservations": 0,
                "miningObservations": 0,
                "naturalFires": 0,
                "persistentEvents": 0,
            }
        states[st]["totalObservations"] += 1
        ml_t = getattr(h, "ml_type", "unknown") or "unknown"
        if ml_t == "industrial_thermal_source":
            states[st]["industrialObservations"] += 1
        elif ml_t == "mining_thermal_source":
            states[st]["miningObservations"] += 1
        elif ml_t == "natural_fire":
            states[st]["naturalFires"] += 1

        if getattr(h, "persistence_count", 0) >= 3:
            states[st]["persistentEvents"] += 1

    result = []
    for st, metrics in sorted(states.items(), key=lambda x: x[1]["totalObservations"], reverse=True):
        result.append({"state": st, **metrics})

    payload = {
        "totalStatesRepresented": len(result),
        "states": result
    }

    await redis_manager.set_cache(canonical_key, json.dumps(payload), ttl_seconds=settings.analytics_cache_ttl_seconds)
    return payload
