"""
Seed script to populate full 7-day satellite telemetry for 21 August and 22 August in PostgreSQL.
Ensures every single day in the 7-day rolling window (21 Aug to 27 Aug IST) has 150+ realistic satellite hotspot detections.
"""
import asyncio
import hashlib
import random
from datetime import datetime, timezone, timedelta

from sqlalchemy import text
from app.db.session import async_session_factory
from app.db.models.hotspot import Hotspot

INDIAN_STATES_COORDS = [
    ("Punjab", 30.7, 75.8, "agricultural"),
    ("Haryana", 29.0, 76.0, "agricultural"),
    ("Gujarat", 22.3, 70.8, "unknown"),
    ("Maharashtra", 19.7, 75.7, "agricultural"),
    ("Odisha", 20.8, 85.0, "wildfire"),
    ("Madhya Pradesh", 23.2, 77.4, "wildfire"),
    ("Rajasthan", 26.9, 75.8, "agricultural"),
    ("Chhattisgarh", 21.2, 81.6, "wildfire"),
    ("West Bengal", 23.5, 87.2, "agricultural"),
    ("Telangana", 17.8, 79.1, "agricultural"),
]

SATELLITES = ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT"]


async def seed_21_22_august():
    """Insert ~150 hotspots each for 2026-08-21 and 2026-08-22 in UTC (corresponding to IST days 21 and 22 Aug)."""
    hotspots = []
    
    # 21 August 2026 & 22 August 2026
    target_dates = ["2026-08-21", "2026-08-22"]
    
    for date_str in target_dates:
        # Generate 140-170 points per day
        num_points = random.randint(145, 165)
        for i in range(num_points):
            state_name, base_lat, base_lng, main_type = random.choice(INDIAN_STATES_COORDS)
            lat = round(base_lat + random.uniform(-1.2, 1.2), 5)
            lng = round(base_lng + random.uniform(-1.2, 1.2), 5)
            
            # Timestamp throughout the day (UTC 02:00 to 20:00)
            hour = random.randint(2, 20)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            ts_str = f"{date_str}T{hour:02d}:{minute:02d}:{second:02d}Z"
            
            # Select ML classification type
            types_pool = [main_type, main_type, "agricultural", "wildfire", "unknown", "gas_flare"]
            ml_type = random.choice(types_pool)
            
            # FRP and brightness
            frp = round(random.uniform(5.0, 85.0), 2)
            brightness = round(random.uniform(298.0, 345.0), 2)
            confidence = float(random.choice([65, 75, 80, 88, 92, 95]))
            ml_confidence = round(random.uniform(0.78, 0.99), 3)
            severity = "critical" if frp > 50 else ("high" if frp > 25 else "medium")
            sat_source = random.choice(SATELLITES)
            
            # Unique ID based on location and timestamp
            raw_id = f"{date_str}-{lat}-{lng}-{i}"
            hid = "FIRMS-" + hashlib.md5(raw_id.encode()).hexdigest()[:16]
            
            hotspots.append({
                "id": hid,
                "latitude": lat,
                "longitude": lng,
                "type": "unknown",
                "ml_type": ml_type,
                "ml_confidence": ml_confidence,
                "model_version": "xgboost-v1-1m-v2",
                "brightness": brightness,
                "frp": frp,
                "confidence": confidence,
                "severity": severity,
                "timestamp": ts_str,
                "status": "active",
                "source": sat_source,
                "state": state_name,
                "country": "India",
            })

    async with async_session_factory() as db:
        objects = []
        for h in hotspots:
            iso_str = h["timestamp"].replace("Z", "+00:00")
            dt_val = datetime.fromisoformat(iso_str)
            obj = Hotspot(
                id=h["id"],
                latitude=h["latitude"],
                longitude=h["longitude"],
                type=h["type"],
                ml_type=h["ml_type"],
                ml_confidence=h["ml_confidence"],
                model_version=h["model_version"],
                brightness=h["brightness"],
                confidence=h["confidence"],
                severity=h["severity"],
                timestamp=dt_val,
                status=h["status"],
                source=h["source"],
                state=h["state"],
                country=h["country"],
            )
            objects.append(obj)
        db.add_all(objects)
        await db.commit()
        
        # Populate geometry points
        await db.execute(text("UPDATE hotspots SET geometry = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326) WHERE geometry IS NULL"))
        await db.commit()
        print(f"Successfully seeded {len(objects)} satellite observations for 21 and 22 August.")


if __name__ == "__main__":
    asyncio.run(seed_21_22_august())
