import asyncio
import os
import sys
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.db.session import async_session_factory
from app.db.models import Hotspot
from app.ml.inference import ml_inference_service
from app.ml.model import model_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_force_backfill():
    logger.info("Initializing ML model for force database backfill...")
    model_manager.load_model()
    logger.info(f"Loaded model version: {model_manager.model_version}")

    async with async_session_factory() as session:
        # Get hotspots that are currently unknown
        result = await session.execute(select(Hotspot).where(Hotspot.ml_type == "unknown"))
        hotspots = result.scalars().all()
        logger.info(f"Found {len(hotspots)} 'unknown' hotspots in database for ML classification force backfill.")

        if not hotspots:
            logger.info("No unknown hotspots found. Exiting.")
            return

        updated_count = 0
        for i, h in enumerate(hotspots):
            try:
                ml_out = await ml_inference_service.predict_observation(
                    db=session,
                    latitude=h.latitude,
                    longitude=h.longitude,
                    timestamp=h.timestamp,
                    frp=h.frp,
                )

                # Update the SQLAlchemy model explicitly
                h.ml_type = ml_out.ml_type
                h.ml_confidence = ml_out.ml_confidence
                h.model_version = ml_out.model_version
                h.ml_explanation = str(ml_out.ml_explanation) if ml_out.ml_explanation else None

                session.add(h)
                updated_count += 1
                
                if (i + 1) % 50 == 0:
                    logger.info(f"Processed {i + 1}/{len(hotspots)}... Last prediction: {ml_out.ml_type} ({ml_out.ml_confidence})")
                    # Flush intermediate changes to be safe
                    await session.flush()

            except Exception as e:
                logger.error(f"Failed to process hotspot {h.id}: {e}")

        # Explicitly commit the transaction
        await session.commit()
        logger.info(f"Successfully force-backfilled and committed {updated_count} hotspots.")

if __name__ == "__main__":
    asyncio.run(run_force_backfill())
