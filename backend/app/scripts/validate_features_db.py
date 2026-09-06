import asyncio
import logging
import math
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy import text, NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings
from app.ml.source_features import build_source_features

logging.basicConfig(level=logging.INFO, format='%(message)s')

def manual_notebook_calculation(rows, osm_dist_deg):
    if not rows:
        return None
        
    df = pd.DataFrame(rows, columns=['lat', 'lon', 'timestamp', 'frp'])
    
    obs_count = len(df)
    
    # FRP stats
    frp_vals = df['frp'].dropna()
    if len(frp_vals) > 0:
        mean_frp = frp_vals.mean()
        # pandas default ddof=1
        std_frp = frp_vals.std() 
        if pd.isna(std_frp): std_frp = 0.0
        
        log_mean_frp = np.log1p(mean_frp)
        log_std_frp = np.log1p(std_frp)
        
        if mean_frp > 0:
            frp_cv = std_frp / mean_frp
        else:
            frp_cv = 0.0
    else:
        log_mean_frp = 0.0
        log_std_frp = 0.0
        frp_cv = 0.0
        
    # Temporal stats
    months = set(df['timestamp'].dt.month)
    months_active = len(months)
    
    min_ts = df['timestamp'].min()
    max_ts = df['timestamp'].max()
    active_duration_days = (max_ts - min_ts).days
    first_seen_month = min_ts.month
    
    nearest_osm_km = osm_dist_deg * 111.0 if osm_dist_deg is not None else 0.0
    
    return {
        "obs_count": float(obs_count),
        "log_mean_frp": float(log_mean_frp),
        "log_std_frp": float(log_std_frp),
        "frp_cv": float(frp_cv),
        "months_active": float(months_active),
        "nearest_osm_distance_km": float(nearest_osm_km),
        "active_duration_days": float(active_duration_days),
        "first_seen_month": float(first_seen_month)
    }

async def main():
    db_url = settings.get_database_url
    engine = create_async_engine(
        db_url, poolclass=NullPool,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    
    async with session_factory() as session:
        # Case 1: Multiple occurrences
        res = await session.execute(text("""
            SELECT ROUND(latitude::numeric, 3) as lat, ROUND(longitude::numeric, 3) as lon
            FROM hotspots
            GROUP BY 1, 2
            HAVING COUNT(*) > 2
            LIMIT 1
        """))
        multi_lat, multi_lon = res.first()
        
        # Case 2: Single occurrence
        res = await session.execute(text("""
            SELECT ROUND(latitude::numeric, 3) as lat, ROUND(longitude::numeric, 3) as lon
            FROM hotspots
            GROUP BY 1, 2
            HAVING COUNT(*) = 1
            LIMIT 1
        """))
        single_lat, single_lon = res.first()
        
        # Case 3: Near OSM feature
        res = await session.execute(text("""
            SELECT latitude, longitude FROM osm_features LIMIT 1
        """))
        osm_lat, osm_lon = res.first()
        
        cases = [
            ("Multiple Observations", multi_lat, multi_lon),
            ("Single Observation", single_lat, single_lon),
            ("Near OSM Feature", osm_lat, osm_lon),
        ]
        
        for name, lat, lon in cases:
            print(f"\\n=== Testing Case: {name} (Lat: {lat}, Lon: {lon}) ===")
            lat = float(lat)
            lon = float(lon)
            
            # 1. Fetch raw data for manual calculation
            cutoff = datetime.now(timezone.utc)
            rows = await session.execute(text("""
                SELECT latitude, longitude, timestamp, frp
                FROM hotspots
                WHERE ROUND(CAST(latitude AS numeric), 3) = ROUND(CAST(:lat AS numeric), 3)
                  AND ROUND(CAST(longitude AS numeric), 3) = ROUND(CAST(:lon AS numeric), 3)
                  AND timestamp <= :cutoff
            """), {"lat": lat, "lon": lon, "cutoff": cutoff})
            raw_data = rows.fetchall()
            
            if not raw_data:
                print(f"  No hotspots found for {name}. Simulating empty.")
                continue
                
            dist_res = await session.execute(text("""
                SELECT SQRT(POWER(latitude - :lat, 2) + POWER(longitude - :lon, 2)) as dist
                FROM osm_features ORDER BY 1 LIMIT 1
            """), {"lat": lat, "lon": lon})
            osm_dist = dist_res.scalar()
            
            # Manual calculate
            manual = manual_notebook_calculation(raw_data, osm_dist)
            
            # Adapter calculate
            try:
                adapter_vec = await build_source_features(db=session, latitude=lat, longitude=lon, cutoff_ts=cutoff)
                adapter = {
                    "obs_count": adapter_vec.obs_count,
                    "log_mean_frp": adapter_vec.log_mean_frp,
                    "log_std_frp": adapter_vec.log_std_frp,
                    "frp_cv": adapter_vec.frp_cv,
                    "months_active": adapter_vec.months_active,
                    "nearest_osm_distance_km": adapter_vec.nearest_osm_distance_km,
                    "active_duration_days": adapter_vec.active_duration_days,
                    "first_seen_month": adapter_vec.first_seen_month
                }
                
                print("  Feature\\t\\tManual (Pandas)\\tAdapter (Prod)\\tMatch?")
                for key in adapter.keys():
                    m_val = manual[key]
                    a_val = adapter[key]
                    match = math.isclose(m_val, a_val, rel_tol=1e-5, abs_tol=1e-5)
                    print(f"  {key[:15]:<15}\\t{m_val:.4f}\\t\\t{a_val:.4f}\\t\\t{'YES' if match else 'NO'}")
            except Exception as e:
                print(f"  Adapter Error: {e}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
