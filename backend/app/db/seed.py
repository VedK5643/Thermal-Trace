"""
Database seed script.
Populates Supabase PostgreSQL with the existing frontend mock data.
Ensures PostGIS is enabled, creates tables, and inserts seed records.

Usage:
    cd backend
    python -m app.db.seed
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db.models.hotspot import Hotspot
from app.db.models.facility import Facility
from app.db.models.alert import Alert

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# ─── Seed Data (from frontend mock JSONs) ──────────────────────

FACILITIES = [
    {"id": "FAC-001", "name": "Reliance Jamnagar Refinery", "type": "refinery", "latitude": 22.3072, "longitude": 70.8022, "city": "Jamnagar", "state": "Gujarat", "country": "India"},
    {"id": "FAC-002", "name": "Adani Power Mundra", "type": "power_plant", "latitude": 23.0225, "longitude": 72.5714, "city": "Ahmedabad", "state": "Gujarat", "country": "India"},
    {"id": "FAC-003", "name": "IOCL Vadodara Refinery", "type": "refinery", "latitude": 22.3100, "longitude": 73.1900, "city": "Vadodara", "state": "Gujarat", "country": "India"},
    {"id": "FAC-004", "name": "Essar Steel Hazira", "type": "steel_plant", "latitude": 21.1702, "longitude": 72.8311, "city": "Surat", "state": "Gujarat", "country": "India"},
    {"id": "FAC-005", "name": "Nayara Energy Vadinar", "type": "refinery", "latitude": 22.4707, "longitude": 70.0577, "city": "Vadinar", "state": "Gujarat", "country": "India"},
    {"id": "FAC-006", "name": "ONGC Hazira Complex", "type": "lng_terminal", "latitude": 20.9500, "longitude": 72.8300, "city": "Hazira", "state": "Gujarat", "country": "India"},
    {"id": "FAC-007", "name": "Gujarat Ambuja Cements", "type": "cement_plant", "latitude": 22.5600, "longitude": 72.9500, "city": "Anand", "state": "Gujarat", "country": "India"},
    {"id": "FAC-008", "name": "Petronet LNG Dahej", "type": "lng_terminal", "latitude": 21.2300, "longitude": 72.8600, "city": "Dahej", "state": "Gujarat", "country": "India"},
    {"id": "FAC-009", "name": "Torrent Power Sabarmati", "type": "power_plant", "latitude": 23.5900, "longitude": 72.3800, "city": "Mehsana", "state": "Gujarat", "country": "India"},
    {"id": "FAC-010", "name": "GSPC LNG Terminal Mundra", "type": "lng_terminal", "latitude": 22.1500, "longitude": 70.1300, "city": "Mundra", "state": "Gujarat", "country": "India"},
    {"id": "FAC-011", "name": "UltraTech Cement Kovaya", "type": "cement_plant", "latitude": 21.4800, "longitude": 71.8500, "city": "Rajula", "state": "Gujarat", "country": "India"},
    {"id": "FAC-012", "name": "Tata Power Mundra UMPP", "type": "power_plant", "latitude": 22.8400, "longitude": 69.7200, "city": "Mundra", "state": "Gujarat", "country": "India"},
    {"id": "FAC-013", "name": "ArcelorMittal Nippon Hazira", "type": "steel_plant", "latitude": 21.1900, "longitude": 72.8100, "city": "Hazira", "state": "Gujarat", "country": "India"},
    {"id": "FAC-014", "name": "GNFC Bharuch", "type": "power_plant", "latitude": 21.7200, "longitude": 73.0000, "city": "Bharuch", "state": "Gujarat", "country": "India"},
    {"id": "FAC-015", "name": "Sanghi Cement Kutch", "type": "cement_plant", "latitude": 22.9300, "longitude": 69.6400, "city": "Kutch", "state": "Gujarat", "country": "India"},
]

HOTSPOTS = [
    {"id": "HS-001", "latitude": 22.3072, "longitude": 70.8022, "type": "industrial_thermal_source", "brightness": 340, "confidence": 92, "severity": "critical", "timestamp": "2026-08-26T08:30:00Z", "facilityId": "FAC-001", "status": "active"},
    {"id": "HS-002", "latitude": 22.2950, "longitude": 70.7900, "type": "industrial_thermal_source", "brightness": 326, "confidence": 88, "severity": "high", "timestamp": "2026-08-25T14:15:00Z", "facilityId": "FAC-001", "status": "active"},
    {"id": "HS-003", "latitude": 22.3150, "longitude": 70.8200, "type": "industrial_thermal_source", "brightness": 318, "confidence": 85, "severity": "high", "timestamp": "2026-08-24T10:00:00Z", "facilityId": "FAC-001", "status": "active"},
    {"id": "HS-004", "latitude": 23.0225, "longitude": 72.5714, "type": "industrial_thermal_source", "brightness": 310, "confidence": 78, "severity": "high", "timestamp": "2026-08-26T06:45:00Z", "facilityId": "FAC-002", "status": "active"},
    {"id": "HS-005", "latitude": 23.0400, "longitude": 72.5500, "type": "industrial_thermal_source", "brightness": 295, "confidence": 82, "severity": "medium", "timestamp": "2026-08-25T22:00:00Z", "facilityId": "FAC-002", "status": "active"},
    {"id": "HS-006", "latitude": 23.0100, "longitude": 72.5900, "type": "industrial_thermal_source", "brightness": 305, "confidence": 74, "severity": "high", "timestamp": "2026-08-24T18:30:00Z", "facilityId": None, "status": "active"},
    {"id": "HS-007", "latitude": 22.3100, "longitude": 73.1900, "type": "industrial_thermal_source", "brightness": 288, "confidence": 90, "severity": "medium", "timestamp": "2026-08-26T04:00:00Z", "facilityId": "FAC-003", "status": "active"},
    {"id": "HS-008", "latitude": 22.2950, "longitude": 73.2100, "type": "industrial_thermal_source", "brightness": 275, "confidence": 86, "severity": "medium", "timestamp": "2026-08-25T16:30:00Z", "facilityId": "FAC-003", "status": "active"},
    {"id": "HS-009", "latitude": 21.1702, "longitude": 72.8311, "type": "industrial_thermal_source", "brightness": 332, "confidence": 91, "severity": "critical", "timestamp": "2026-08-26T07:15:00Z", "facilityId": "FAC-004", "status": "active"},
    {"id": "HS-010", "latitude": 21.1850, "longitude": 72.8200, "type": "industrial_thermal_source", "brightness": 298, "confidence": 80, "severity": "medium", "timestamp": "2026-08-25T20:00:00Z", "facilityId": "FAC-004", "status": "active"},
    {"id": "HS-011", "latitude": 21.1600, "longitude": 72.8500, "type": "industrial_thermal_source", "brightness": 315, "confidence": 76, "severity": "high", "timestamp": "2026-08-24T12:00:00Z", "facilityId": None, "status": "active"},
    {"id": "HS-012", "latitude": 22.4707, "longitude": 70.0577, "type": "industrial_thermal_source", "brightness": 350, "confidence": 95, "severity": "critical", "timestamp": "2026-08-26T09:00:00Z", "facilityId": "FAC-005", "status": "active"},
    {"id": "HS-013", "latitude": 22.4500, "longitude": 70.0800, "type": "industrial_thermal_source", "brightness": 338, "confidence": 93, "severity": "critical", "timestamp": "2026-08-25T11:00:00Z", "facilityId": "FAC-005", "status": "active"},
    {"id": "HS-014", "latitude": 22.4900, "longitude": 70.0400, "type": "industrial_thermal_source", "brightness": 312, "confidence": 70, "severity": "high", "timestamp": "2026-08-24T08:30:00Z", "facilityId": "FAC-005", "status": "active"},
    {"id": "HS-015", "latitude": 22.4600, "longitude": 70.0650, "type": "industrial_thermal_source", "brightness": 320, "confidence": 87, "severity": "high", "timestamp": "2026-08-23T15:00:00Z", "facilityId": "FAC-005", "status": "active"},
    {"id": "HS-016", "latitude": 23.2156, "longitude": 69.6669, "type": "unknown", "brightness": 260, "confidence": 55, "severity": "low", "timestamp": "2026-08-26T03:00:00Z", "facilityId": None, "status": "monitoring"},
    {"id": "HS-017", "latitude": 23.3000, "longitude": 69.7500, "type": "unknown", "brightness": 248, "confidence": 48, "severity": "low", "timestamp": "2026-08-25T09:00:00Z", "facilityId": None, "status": "monitoring"},
    {"id": "HS-018", "latitude": 22.8000, "longitude": 71.6000, "type": "natural_fire", "brightness": 270, "confidence": 65, "severity": "low", "timestamp": "2026-08-26T05:30:00Z", "facilityId": None, "status": "active"},
    {"id": "HS-019", "latitude": 22.7500, "longitude": 71.5500, "type": "natural_fire", "brightness": 265, "confidence": 62, "severity": "low", "timestamp": "2026-08-25T07:00:00Z", "facilityId": None, "status": "active"},
    {"id": "HS-020", "latitude": 22.8500, "longitude": 71.6500, "type": "natural_fire", "brightness": 258, "confidence": 60, "severity": "low", "timestamp": "2026-08-24T06:00:00Z", "facilityId": None, "status": "active"},
    {"id": "HS-021", "latitude": 21.7645, "longitude": 72.1519, "type": "natural_fire", "brightness": 290, "confidence": 72, "severity": "medium", "timestamp": "2026-08-26T02:00:00Z", "facilityId": None, "status": "active"},
    {"id": "HS-022", "latitude": 21.7800, "longitude": 72.1700, "type": "natural_fire", "brightness": 282, "confidence": 68, "severity": "medium", "timestamp": "2026-08-25T18:00:00Z", "facilityId": None, "status": "active"},
    {"id": "HS-023", "latitude": 21.7400, "longitude": 72.1300, "type": "natural_fire", "brightness": 275, "confidence": 64, "severity": "medium", "timestamp": "2026-08-24T14:00:00Z", "facilityId": None, "status": "active"},
    {"id": "HS-024", "latitude": 20.9500, "longitude": 72.8300, "type": "industrial_thermal_source", "brightness": 308, "confidence": 83, "severity": "high", "timestamp": "2026-08-26T01:00:00Z", "facilityId": "FAC-006", "status": "active"},
    {"id": "HS-025", "latitude": 20.9300, "longitude": 72.8100, "type": "industrial_thermal_source", "brightness": 292, "confidence": 77, "severity": "medium", "timestamp": "2026-08-25T12:00:00Z", "facilityId": "FAC-006", "status": "active"},
    {"id": "HS-026", "latitude": 22.3039, "longitude": 70.8022, "type": "industrial_thermal_source", "brightness": 345, "confidence": 94, "severity": "critical", "timestamp": "2026-08-22T10:00:00Z", "facilityId": "FAC-001", "status": "active"},
    {"id": "HS-027", "latitude": 22.3100, "longitude": 70.7950, "type": "industrial_thermal_source", "brightness": 330, "confidence": 89, "severity": "critical", "timestamp": "2026-08-21T16:00:00Z", "facilityId": "FAC-001", "status": "active"},
    {"id": "HS-028", "latitude": 22.3200, "longitude": 70.8100, "type": "industrial_thermal_source", "brightness": 318, "confidence": 81, "severity": "high", "timestamp": "2026-08-20T12:00:00Z", "facilityId": "FAC-001", "status": "active"},
    {"id": "HS-029", "latitude": 23.0300, "longitude": 72.5800, "type": "industrial_thermal_source", "brightness": 280, "confidence": 71, "severity": "medium", "timestamp": "2026-08-23T08:00:00Z", "facilityId": "FAC-002", "status": "active"},
    {"id": "HS-030", "latitude": 22.4800, "longitude": 70.0700, "type": "industrial_thermal_source", "brightness": 342, "confidence": 92, "severity": "critical", "timestamp": "2026-08-22T14:00:00Z", "facilityId": "FAC-005", "status": "active"},
    {"id": "HS-031", "latitude": 22.4650, "longitude": 70.0550, "type": "industrial_thermal_source", "brightness": 325, "confidence": 86, "severity": "high", "timestamp": "2026-08-21T10:00:00Z", "facilityId": "FAC-005", "status": "active"},
    {"id": "HS-032", "latitude": 21.1750, "longitude": 72.8400, "type": "industrial_thermal_source", "brightness": 300, "confidence": 75, "severity": "high", "timestamp": "2026-08-23T20:00:00Z", "facilityId": "FAC-004", "status": "active"},
    {"id": "HS-033", "latitude": 23.7800, "longitude": 71.6300, "type": "natural_fire", "brightness": 255, "confidence": 58, "severity": "low", "timestamp": "2026-08-22T06:00:00Z", "facilityId": None, "status": "active"},
    {"id": "HS-034", "latitude": 23.8200, "longitude": 71.6800, "type": "natural_fire", "brightness": 250, "confidence": 56, "severity": "low", "timestamp": "2026-08-21T08:00:00Z", "facilityId": None, "status": "active"},
    {"id": "HS-035", "latitude": 22.5600, "longitude": 72.9500, "type": "industrial_thermal_source", "brightness": 302, "confidence": 79, "severity": "high", "timestamp": "2026-08-20T20:00:00Z", "facilityId": "FAC-007", "status": "active"},
    {"id": "HS-036", "latitude": 21.2300, "longitude": 72.8600, "type": "industrial_thermal_source", "brightness": 285, "confidence": 73, "severity": "medium", "timestamp": "2026-08-22T08:00:00Z", "facilityId": "FAC-008", "status": "active"},
    {"id": "HS-037", "latitude": 22.6900, "longitude": 69.8600, "type": "unknown", "brightness": 245, "confidence": 50, "severity": "low", "timestamp": "2026-08-23T04:00:00Z", "facilityId": None, "status": "monitoring"},
    {"id": "HS-038", "latitude": 21.5200, "longitude": 70.4600, "type": "natural_fire", "brightness": 278, "confidence": 66, "severity": "medium", "timestamp": "2026-08-20T15:00:00Z", "facilityId": None, "status": "active"},
    {"id": "HS-039", "latitude": 23.5900, "longitude": 72.3800, "type": "industrial_thermal_source", "brightness": 296, "confidence": 76, "severity": "medium", "timestamp": "2026-08-21T22:00:00Z", "facilityId": "FAC-009", "status": "active"},
    {"id": "HS-040", "latitude": 22.1500, "longitude": 70.1300, "type": "industrial_thermal_source", "brightness": 310, "confidence": 84, "severity": "high", "timestamp": "2026-08-26T08:00:00Z", "facilityId": "FAC-010", "status": "active"},
]

ALERTS = [
    {"id": "ALT-010", "hotspotId": "HS-001", "facilityId": "FAC-001", "severity": "critical", "title": "Critical Industrial Flare", "message": "High intensity thermal event detected at Reliance Jamnagar Refinery.", "timestamp": "2026-08-27T08:35:00Z", "acknowledged": False},
    {"id": "ALT-011", "hotspotId": "HS-012", "facilityId": "FAC-005", "severity": "critical", "title": "Severe Anomaly Monitored", "message": "Elevated flare emission detected at Nayara Energy Vadinar.", "timestamp": "2026-08-27T09:15:00Z", "acknowledged": False},
    {"id": "ALT-012", "hotspotId": "HS-009", "facilityId": "FAC-004", "severity": "warning", "title": "Industrial Heat Event", "message": "Thermal anomaly detected near Essar Steel Hazira Complex.", "timestamp": "2026-08-27T07:20:00Z", "acknowledged": False},
    {"id": "ALT-013", "hotspotId": "HS-007", "facilityId": "FAC-003", "severity": "warning", "title": "Elevated Flaring", "message": "Gas flare activity exceeding baseline at IOCL Vadodara.", "timestamp": "2026-08-27T04:10:00Z", "acknowledged": False},
    {"id": "ALT-014", "hotspotId": "HS-024", "facilityId": "FAC-006", "severity": "info", "title": "Thermal Observation", "message": "Thermal activity monitored near ONGC Hazira Complex.", "timestamp": "2026-08-27T02:15:00Z", "acknowledged": False},
    {"id": "ALT-001", "hotspotId": "HS-001", "facilityId": "FAC-001", "severity": "critical", "title": "Critical Anomaly", "message": "Sustained high thermal signature at Reliance Jamnagar Refinery.", "timestamp": "2026-08-26T08:35:00Z", "acknowledged": False},
    {"id": "ALT-002", "hotspotId": "HS-012", "facilityId": "FAC-005", "severity": "critical", "title": "Severe Flare Detected", "message": "Abnormal flaring detected at Nayara Energy Vadinar.", "timestamp": "2026-08-26T09:05:00Z", "acknowledged": False},
    {"id": "ALT-003", "hotspotId": "HS-009", "facilityId": "FAC-004", "severity": "critical", "title": "Industrial Thermal Alert", "message": "High intensity thermal event at Essar Steel Hazira.", "timestamp": "2026-08-26T07:20:00Z", "acknowledged": False},
    {"id": "ALT-004", "hotspotId": "HS-007", "facilityId": "FAC-003", "severity": "warning", "title": "Elevated Flaring", "message": "Gas flare activity exceeding baseline at IOCL Vadodara.", "timestamp": "2026-08-26T04:10:00Z", "acknowledged": False},
    {"id": "ALT-005", "hotspotId": "HS-024", "facilityId": "FAC-006", "severity": "warning", "title": "Unusual Heat Signature", "message": "Potential industrial thermal source near ONGC Hazira Complex.", "timestamp": "2026-08-26T01:15:00Z", "acknowledged": False},
    {"id": "ALT-006", "hotspotId": "HS-021", "facilityId": None, "severity": "warning", "title": "Wildfire Monitored", "message": "Wildfire detected in open terrain. Monitoring spread.", "timestamp": "2026-08-26T02:05:00Z", "acknowledged": True},
    {"id": "ALT-007", "hotspotId": "HS-016", "facilityId": None, "severity": "info", "title": "Unknown Source", "message": "Low confidence thermal anomaly detected.", "timestamp": "2026-08-26T03:30:00Z", "acknowledged": True},
    {"id": "ALT-008", "hotspotId": "HS-018", "facilityId": None, "severity": "info", "title": "Agricultural Fire", "message": "Likely crop burning activity detected.", "timestamp": "2026-08-26T05:40:00Z", "acknowledged": False},
]


def _parse_ts(ts_str: str) -> datetime:
    """Parse ISO timestamp string to datetime."""
    return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))


def _make_point_wkt(longitude: float, latitude: float) -> str:
    """Create WKT POINT string: SRID=4326;POINT(longitude latitude)."""
    return f"SRID=4326;POINT({longitude} {latitude})"


async def seed_database():
    """Seed the database with mock data."""
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        # Enable PostGIS extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        logger.info("PostGIS extension enabled")

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")

    async with session_factory() as session:
        # Check if data already exists
        result = await session.execute(text("SELECT COUNT(*) FROM facilities"))
        count = result.scalar()
        if count and count > 0:
            logger.info("Database already seeded (%d facilities found). Skipping.", count)
            return

        # Insert facilities first (referenced by hotspots)
        for f in FACILITIES:
            facility = Facility(
                id=f["id"],
                name=f["name"],
                type=f["type"],
                latitude=f["latitude"],
                longitude=f["longitude"],
                city=f["city"],
                state=f["state"],
                country=f["country"],
                geometry=_make_point_wkt(f["longitude"], f["latitude"]),
            )
            session.add(facility)
        await session.flush()
        logger.info("Inserted %d facilities", len(FACILITIES))

        # Insert hotspots
        for h in HOTSPOTS:
            hotspot = Hotspot(
                id=h["id"],
                latitude=h["latitude"],
                longitude=h["longitude"],
                type=h["type"],
                brightness=h["brightness"],
                confidence=h["confidence"],
                severity=h["severity"],
                timestamp=_parse_ts(h["timestamp"]),
                facility_id=h["facilityId"],
                status=h["status"],
                state="Gujarat",
                country="India",
                geometry=_make_point_wkt(h["longitude"], h["latitude"]),
            )
            await session.merge(hotspot)
        await session.flush()
        logger.info("Merged %d hotspots", len(HOTSPOTS))

        # Insert / merge alerts
        for a in ALERTS:
            alert = Alert(
                id=a["id"],
                hotspot_id=a["hotspotId"],
                facility_id=a["facilityId"],
                severity=a["severity"],
                title=a["title"],
                message=a["message"],
                timestamp=_parse_ts(a["timestamp"]),
                acknowledged=a["acknowledged"],
            )
            await session.merge(alert)
        await session.flush()
        logger.info("Merged %d alerts", len(ALERTS))

        await session.commit()
        logger.info("Database seeding complete!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_database())
