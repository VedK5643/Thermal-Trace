import asyncio
import sys
import json
from datetime import timezone

sys.path.append("e:\\VEDAGYA\\Thermal Trace\\Thermal-Trace\\backend")

from sqlalchemy import select, func, text
from app.db.session import async_session_factory
from app.db.models.hotspot import Hotspot
from app.db.models.osm_feature import OSMFeature
from app.ml.source_features import build_source_features, SourceFeatureVector
from app.ml.inference import MLInferenceService

async def audit_classification():
    async with async_session_factory() as db:
        print("=== PRODUCTION CLASS COUNTS ===")
        stmt = select(Hotspot.ml_type, func.count(Hotspot.id)).group_by(Hotspot.ml_type)
        res = await db.execute(stmt)
        for row in res.all():
            print(f"{row[0]}: {row[1]}")

        print("\n=== OSM AVAILABILITY ===")
        stmt = select(func.count(OSMFeature.id))
        osm_count = (await db.execute(stmt)).scalar()
        print(f"Total OSM features in production: {osm_count}")

        print("\n=== mlExplanation DISTRIBUTION ===")
        stmt = select(Hotspot.ml_explanation, func.count(Hotspot.id)).where(Hotspot.ml_type == 'unknown').group_by(Hotspot.ml_explanation)
        res = await db.execute(stmt)
        for row in res.all():
            print(f"{row[0]}: {row[1]}")

        print("\n=== TRACE ONE REAL HOTSPOT ===")
        # Get one hotspot that is currently unknown
        stmt = select(Hotspot).where(Hotspot.ml_type == 'unknown').limit(1)
        hotspot = (await db.execute(stmt)).scalar_one_or_none()
        if not hotspot:
            print("No unknown hotspots found.")
            return

        print(f"Hotspot ID: {hotspot.id}")
        print(f"Location: {hotspot.latitude}, {hotspot.longitude}")
        print(f"Observation Time: {hotspot.timestamp}")
        print(f"Current Class: {hotspot.ml_type}")
        print(f"Current Confidence: {hotspot.ml_confidence}")
        print(f"Current Explanation: {hotspot.ml_explanation}")

        # Let's try reclassifying it
        print("\nReclassifying with current OSM data...")
        ml_service = MLInferenceService()
        
        # Build features manually for trace
        try:
            features = await build_source_features(
                db=db,
                latitude=hotspot.latitude,
                longitude=hotspot.longitude,
                cutoff_ts=hotspot.timestamp,
                current_frp=hotspot.frp,
                allow_single_obs_fallback=True,
            )
            print("Successfully built features:")
            print(f"  obs_count: {features.obs_count}")
            print(f"  log_mean_frp: {features.log_mean_frp}")
            print(f"  log_std_frp: {features.log_std_frp}")
            print(f"  frp_cv: {features.frp_cv}")
            print(f"  months_active: {features.months_active}")
            print(f"  nearest_osm_distance_km: {features.nearest_osm_distance_km}")
            print(f"  active_duration_days: {features.active_duration_days}")
            print(f"  first_seen_month: {features.first_seen_month}")

            # Run inference
            pred = await ml_service.predict_observation(
                db=db,
                latitude=hotspot.latitude,
                longitude=hotspot.longitude,
                timestamp=hotspot.timestamp,
                frp=hotspot.frp,
            )
            print(f"\nNew Prediction:")
            print(f"  ml_type: {pred.ml_type}")
            print(f"  ml_confidence: {pred.ml_confidence}")
            print(f"  ml_explanation: {pred.ml_explanation}")

        except Exception as e:
            print(f"Error during feature building: {e}")

if __name__ == "__main__":
    asyncio.run(audit_classification())
