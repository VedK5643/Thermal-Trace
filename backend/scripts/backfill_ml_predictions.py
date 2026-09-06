"""
Database ML Backfill Script for Live NASA FIRMS Observations.
Runs frozen XGBoost V2 model (xgboost-v1-1m-v2) on all stored FIRMS records in Supabase PostgreSQL database.
Populates ml_type, ml_confidence, model_version, and ml_explanation idempotently while preserving raw telemetry.
"""
import asyncio
import os
import sys
import logging

# Add backend root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.db.session import async_session_factory
from app.db.models import Hotspot
from app.ml.inference import ml_inference_service
from app.ml.model import model_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_backfill():
    logger.info("Initializing ML model for database backfill...")
    model_manager.load_model()
    logger.info(f"Loaded model version: {model_manager.model_version}")

    async with async_session_factory() as session:
        result = await session.execute(select(Hotspot))
        hotspots = result.scalars().all()
        logger.info(f"Found {len(hotspots)} hotspots in database for ML classification backfill.")

        updated_count = 0
        for h in hotspots:
            # 10-Feature Inference
            ml_out = ml_inference_service.predict_observation(
                brightness=h.brightness,
                bright_ti5=getattr(h, "bright_ti5", None),
                frp=getattr(h, "frp", None),
                confidence=h.confidence,
                latitude=h.latitude,
                longitude=h.longitude,
                timestamp=h.timestamp,
                facility_dist_km=getattr(h, "facility_dist_km", None),
                persistence_count=getattr(h, "persistence_count", None),
            )

            h.ml_type = ml_out.ml_type
            h.ml_confidence = ml_out.ml_confidence
            h.model_version = ml_out.model_version
            h.ml_explanation = str(ml_out.ml_explanation) if ml_out.ml_explanation else None
            updated_count += 1

        await session.commit()
        logger.info(f"Successfully backfilled {updated_count} hotspots with model '{model_manager.model_version}' predictions.")


if __name__ == "__main__":
    asyncio.run(run_backfill())
