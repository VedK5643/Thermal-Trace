"""
Model Loader Singleton.
Loads trained XGBoost model from backend/app/ml/models/xgboost_v1.joblib into memory once on startup.
"""
import os
import logging
import joblib
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

ML_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(ML_DIR, "models", "thermalwatch_model.joblib")


class MLModelManager:
    """Thread-safe singleton managing ML model lifecycle and inference execution."""

    _instance: Optional["MLModelManager"] = None
    _model: Any = None
    _class_names: List[str] = ["industrial_thermal_source", "mining_thermal_source", "natural_fire", "unknown"]
    _feature_columns: List[str] = [
        "obs_count", "log_mean_frp", "log_std_frp", "frp_cv",
        "months_active", "nearest_osm_distance_km", "active_duration_days", "first_seen_month"
    ]
    _model_version: str = "thermalwatch-v1"
    _loaded: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MLModelManager, cls).__new__(cls)
        return cls._instance

    def load_model(self) -> bool:
        """Loads model weights from joblib file into memory."""
        if self._loaded and self._model is not None:
            return True

        if not os.path.exists(MODEL_PATH):
            logger.warning(f"ML Model file not found at {MODEL_PATH}. Running in abstention mode.")
            return False

        try:
            artifact = joblib.load(MODEL_PATH)
            if isinstance(artifact, dict):
                self._model = artifact.get("model")
                self._class_names = artifact.get("class_names", self._class_names)
                self._feature_columns = artifact.get("feature_columns", self._feature_columns)
                self._model_version = artifact.get("model_version", self._model_version)
            else:
                self._model = artifact

            self._loaded = True
            logger.info(f"Successfully loaded ML model version '{self._model_version}' into memory.")
            return True
        except Exception as e:
            logger.error(f"Error loading ML model from {MODEL_PATH}: {e}")
            return False

    @property
    def is_loaded(self) -> bool:
        return self._loaded and self._model is not None

    @property
    def model(self) -> Any:
        return self._model

    @property
    def class_names(self) -> List[str]:
        return self._class_names

    @property
    def feature_columns(self) -> List[str]:
        return self._feature_columns

    @property
    def model_version(self) -> str:
        return self._model_version


model_manager = MLModelManager()
