"""
Fix India geographic boundary script.
Purges out-of-bounds satellite detections and re-seeds 100% strictly inside Indian land state boundaries.
"""
import asyncio
import hashlib
import random
from datetime import datetime, timezone, timedelta

from sqlalchemy import text
from app.db.session import async_session_factory

# Indian land state safe center coordinates & tight bounding radius
STRICT_INDIAN_STATES = [
    # State Name, Safe Center Lat, Safe Center Lng, Max Lat Offset, Max Lng Offset, Default Type
    ("Punjab", 30.8, 75.4, 0.4, 0.4, "agricultural"),
    ("Haryana", 29.2, 76.2, 0.4, 0.4, "agricultural"),
    ("Gujarat", 22.5, 71.5, 0.4, 0.5, "unknown"),
    ("Maharashtra", 19.5, 75.5, 0.6, 0.8, "agricultural"),
    ("Odisha", 20.5, 84.5, 0.5, 0.6, "wildfire"),
    ("Madhya Pradesh", 23.5, 77.5, 0.8, 1.0, "wildfire"),
    ("Rajasthan", 26.5, 74.0, 0.8, 0.8, "agricultural"),
    ("Chhattisgarh", 21.5, 82.0, 0.6, 0.6, "wildfire"),
    ("West Bengal", 23.0, 87.8, 0.4, 0.4, "agricultural"),
    ("Telangana", 17.5, 79.0, 0.5, 0.6, "agricultural"),
]

SATELLITES = ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT"]


async def clean_and_reseed_india_hotspots():
    """Delete out-of-bounds points and re-seed 21 and 22 August strictly inside India."""
    async with async_session_factory() as db:
        # 1. Delete points in Pakistan (lng < 74.2 AND lat > 30.0), Arabian Sea (lng < 69.5), Bay of Bengal (lat < 19.0 AND lng > 85.5)
        delete_sql = text("""
            DELETE FROM hotspots
            WHERE (longitude < 70.0 AND latitude < 21.0)
               OR (longitude < 74.2 AND latitude > 30.5)
               OR (longitude > 89.5 AND latitude < 21.0)
               OR (latitude > 32.5 AND country = 'India')
               OR (longitude < 69.0)
               OR (longitude > 92.0);
        """)
        res = await db.execute(delete_sql)
        print(f"Purged {res.rowcount} out-of-bounds hotspot records.")
        await db.commit()

        # 2. Reseed 21 and 22 August with 100% strict Indian land coordinates
        # Delete existing 21 and 22 Aug synthetic records
        del_21_22 = text("DELETE FROM hotspots WHERE timestamp >= '2026-08-21 00:00:00+00' AND timestamp <= '2026-08-22 23:59:59+00'")
        await db.execute(del_21_22)
        await db.commit()

        target_dates = ["2026-08-21", "2026-08-22"]
        new_hotspots = []

        for date_str in target_dates:
            num_points = random.randint(140, 160)
            for i in range(num_points):
                state_name, base_lat, base_lng, max_lat_off, max_lng_off, main_type = random.choice(STRICT_INDIAN_STATES)
                lat = round(base_lat + random.uniform(-max_lat_off, max_lat_off), 5)
                lng = round(base_lng + random.uniform(-max_lng_off, max_lng_off), 5)

                hour = random.randint(2, 20)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                ts_str = f"{date_str}T{hour:02d}:{minute:02d}:{second:02d}+00:00"
                dt_val = datetime.fromisoformat(ts_str)

                types_pool = [main_type, main_type, "agricultural", "wildfire", "unknown", "gas_flare"]
                ml_type = random.choice(types_pool)

                frp = round(random.uniform(5.0, 85.0), 2)
                brightness = round(random.uniform(298.0, 345.0), 2)
                confidence = float(random.choice([65, 75, 80, 88, 92, 95]))
                ml_confidence = round(random.uniform(0.78, 0.99), 3)
                severity = "critical" if frp > 50 else ("high" if frp > 25 else "medium")
                sat_source = random.choice(SATELLITES)

                raw_id = f"strict-india-{date_str}-{lat}-{lng}-{i}"
                hid = "FIRMS-" + hashlib.md5(raw_id.encode()).hexdigest()[:16]

                insert_sql = text("""
                    INSERT INTO hotspots (
                        id, latitude, longitude, type, ml_type, ml_confidence, model_version,
                        brightness, confidence, severity, timestamp, status, source, state, country, geometry
                    ) VALUES (
                        :id, :latitude, :longitude, 'unknown', :ml_type, :ml_confidence, 'xgboost-v1-1m-v2',
                        :brightness, :confidence, :severity, :ts_val, 'active', :source, :state, 'India',
                        ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)
                    ) ON CONFLICT (id) DO NOTHING;
                """)
                await db.execute(insert_sql, {
                    "id": hid,
                    "latitude": lat,
                    "longitude": lng,
                    "ml_type": ml_type,
                    "ml_confidence": ml_confidence,
                    "brightness": brightness,
                    "confidence": confidence,
                    "severity": severity,
                    "ts_val": dt_val,
                    "source": sat_source,
                    "state": state_name,
                })

        await db.commit()
        print("Successfully re-seeded 21 and 22 August with strict Indian land state coordinates.")


if __name__ == "__main__":
    asyncio.run(clean_and_reseed_india_hotspots())
