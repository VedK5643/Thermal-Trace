"""
Unit and integration tests for ThermalTrace Phase 7 ML classification pipeline.
"""
import pytest
from app.ml.model import model_manager
from app.ml.inference import ml_inference_service
from app.schemas.hotspot import HotspotResponse


def test_model_manager_loading():
    assert model_manager.load_model() is True
    assert model_manager.is_loaded is True
    assert model_manager.model_version == "thermalwatch-v1"

    # Enforce exactly 4 classes
    assert len(model_manager.class_names) == 4
    assert "industrial_thermal_source" in model_manager.class_names
    assert "mining_thermal_source" in model_manager.class_names
    assert "natural_fire" in model_manager.class_names
    assert "unknown" in model_manager.class_names

    # Enforce exactly 8 features
    assert len(model_manager.feature_columns) == 8
    assert model_manager.feature_columns == [
        "obs_count",
        "log_mean_frp",
        "log_std_frp",
        "frp_cv",
        "months_active",
        "nearest_osm_distance_km",
        "active_duration_days",
        "first_seen_month"
    ]


def test_hotspot_schema_ml_fields():
    data = {
        "id": "test-123",
        "latitude": 22.3,
        "longitude": 70.8,
        "type": "unknown",
        "brightness": 340.0,
        "confidence": 90.0,
        "severity": "high",
        "timestamp": "2026-08-26T12:00:00Z",
        "facilityId": None,
        "status": "active",
        "mlType": "industrial_thermal_source",
        "mlConfidence": 0.88,
        "modelVersion": "thermalwatch-v1",
        "mlExplanation": '{"obs_count": 50, "nearest_osm_distance_km": 0.30}'
    }
    schema = HotspotResponse.model_validate(data)
    assert schema.type == "unknown"
    assert schema.ml_type == "industrial_thermal_source"
    assert schema.ml_confidence == 0.88
    assert schema.model_version == "thermalwatch-v1"
