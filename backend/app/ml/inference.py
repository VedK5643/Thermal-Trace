"""
Production ML Inference Service.
Runs real-time prediction on satellite observations and produces feature explanations (SHAP/Feature Importance).
"""
import logging
from typing import Any, Dict, List, Optional
import numpy as np

from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.source_features import build_source_features, InsufficientHistoryError, MissingOSMDataError
from app.ml.model import model_manager
from app.ml.schemas import MLPredictionOutput, HotspotMLType

logger = logging.getLogger(__name__)

# Minimum confidence threshold required for non-unknown classification
CONFIDENCE_ABSTENTION_THRESHOLD = 0.45


class MLInferenceService:
    """Service executing real-time ML classification and explanation."""

    def __init__(self):
        # Ensure model is loaded into memory
        model_manager.load_model()

    async def predict_observation(
        self,
        db: AsyncSession,
        *,
        latitude: float,
        longitude: float,
        timestamp: Any,
        frp: Optional[float] = None,
    ) -> MLPredictionOutput:
        """Runs ML inference on a single thermal observation using historical DB features."""
        if not model_manager.is_loaded:
            model_manager.load_model()

        # Fallback if model loading fails
        if not model_manager.is_loaded:
            return MLPredictionOutput(
                ml_type="unknown",
                ml_confidence=0.0,
                model_version="thermalwatch-v1",
                ml_explanation={"status": "Model uninitialized"}
            )

        try:
            # 1. Feature Extraction (Async DB query)
            feature_vector = await build_source_features(
                db=db,
                latitude=latitude,
                longitude=longitude,
                cutoff_ts=timestamp,
                current_frp=frp,
                allow_single_obs_fallback=True,
            )

            X_val = np.array([feature_vector.to_list()], dtype=np.float32)

            # 2. XGBoost Predict Proba
            model = model_manager.model
            probabilities = model.predict_proba(X_val)[0]
            class_names = model_manager.class_names

            max_idx = int(np.argmax(probabilities))
            max_prob = float(probabilities[max_idx])
            pred_class = class_names[max_idx]

            # 3. Abstention Check (if confidence < 0.45, return 'unknown')
            if max_prob < CONFIDENCE_ABSTENTION_THRESHOLD:
                final_type: HotspotMLType = "unknown"
            else:
                final_type = pred_class if pred_class in ("industrial_thermal_source", "mining_thermal_source", "natural_fire", "unknown") else "unknown"

            return MLPredictionOutput(
                ml_type=final_type,
                ml_confidence=round(max_prob, 3),
                model_version=model_manager.model_version,
                ml_explanation=None
            )

        except InsufficientHistoryError as e:
            logger.info(f"Insufficient history for inference: {e}")
            return MLPredictionOutput(
                ml_type="unknown",
                ml_confidence=0.0,
                model_version=model_manager.model_version,
                ml_explanation={"error": "Insufficient history"}
            )
        except MissingOSMDataError as e:
            logger.error(f"Missing OSM data: {e}")
            return MLPredictionOutput(
                ml_type="unknown",
                ml_confidence=0.0,
                model_version=model_manager.model_version,
                ml_explanation={"error": "Missing OSM data"}
            )
        except Exception as e:
            logger.error(f"ML inference error: {e}", exc_info=True)
            return MLPredictionOutput(
                ml_type="unknown",
                ml_confidence=0.0,
                model_version=model_manager.model_version,
                ml_explanation={"error": str(e)}
            )

    async def predict_batch(
        self,
        db: AsyncSession,
        observations: List[Dict[str, Any]]
    ) -> List[MLPredictionOutput]:
        """Runs ML inference on a list of thermal observation dicts."""
        results = []
        for obs in observations:
            res = await self.predict_observation(
                db=db,
                latitude=obs.get("latitude", 0.0),
                longitude=obs.get("longitude", 0.0),
                timestamp=obs.get("timestamp"),
            )
            results.append(res)
        return results


ml_inference_service = MLInferenceService()
