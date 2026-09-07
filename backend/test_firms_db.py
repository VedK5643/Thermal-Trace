import asyncio
import sys
import logging
from sqlalchemy import text
sys.path.append("e:\\VEDAGYA\\Thermal Trace\\Thermal-Trace\\backend")

from app.db.session import async_session_factory
from app.integrations.firms.normalizer import parse_firms_csv

logging.basicConfig(level=logging.INFO)

csv_text = """latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight
27.85909,95.18375,328.42,0.32,0.55,2026-09-06,620,N,VIIRS,n,2.0NRT,289.01,2.18,D
"""

async def test_insert():
    records = parse_firms_csv(csv_text, "VIIRS_SNPP_NRT")
    record = records[0]
    
    params = {**record}
    params["geom_lon"] = record.get("longitude")
    params["geom_lat"] = record.get("latitude")
    params.setdefault("source", None)
    params["frp"] = record.get("frp")
    params["ml_type"] = "unknown"
    params["ml_confidence"] = 0.0
    params["model_version"] = "test-v1"
    params["ml_explanation"] = None
    params["land_cover_class"] = None
    params["land_cover_name"] = None

    upsert_sql = text("""
        INSERT INTO hotspots (
            id, latitude, longitude, type, brightness, confidence,
            severity, timestamp, facility_id, status,
            country, state, city, district, source, geometry,
            ml_type, ml_confidence, model_version, ml_explanation, frp,
            land_cover_class, land_cover_name
        )
        VALUES (
            :id, :latitude, :longitude, :type, :brightness, :confidence,
            :severity, :timestamp, :facility_id, :status,
            :country, :state, :city, :district, :source,
            ST_SetSRID(ST_MakePoint(CAST(:geom_lon AS float8), CAST(:geom_lat AS float8)), 4326),
            :ml_type, :ml_confidence, :model_version, :ml_explanation, :frp,
            :land_cover_class, :land_cover_name
        )
        ON CONFLICT (id) DO NOTHING
        RETURNING id
    """)

    async with async_session_factory() as db:
        try:
            result = await db.execute(upsert_sql, params)
            print("Execute successful!")
            row = result.fetchone()
            print("Fetched row:", row)
            await db.rollback()
        except Exception as e:
            print("DB Execute Exception:", type(e))
            print("Exception details:", str(e))

if __name__ == "__main__":
    asyncio.run(test_insert())
