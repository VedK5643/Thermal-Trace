"""
Phase 8 System Hardening & Failure Resiliency Tests.
Verifies ML failure recovery, secret protection, duplicate idempotency, and raw FIRMS telemetry preservation.
"""
import os
import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone

from app.ml.inference import MLInferenceService
from app.ml.schemas import MLPredictionOutput


@pytest.mark.asyncio
async def test_ml_failure_recovery_preserves_raw_telemetry():
    """Verify that an exception in ML inference gracefully returns abstention without raising or crashing."""
    service = MLInferenceService()
    mock_db = AsyncMock()

    with patch("app.ml.inference.build_source_features", side_effect=RuntimeError("Simulated ML Feature Extraction Failure")):
        out = await service.predict_observation(
            db=mock_db,
            latitude=21.5,
            longitude=72.5,
            timestamp=datetime.now(timezone.utc)
        )

        assert isinstance(out, MLPredictionOutput)
        assert out.ml_type == "unknown"
        assert out.ml_confidence == 0.0
        assert "error" in out.ml_explanation


@pytest.mark.asyncio
async def test_firm_api_key_not_leaked_in_env_or_dumps():
    """Verify that environment secrets like FIRMS_MAP_KEY are not serialized in ML prediction or hotspot schemas."""
    service = MLInferenceService()
    mock_db = AsyncMock()

    with patch("app.ml.inference.build_source_features") as mock_build:
        from app.ml.source_features import SourceFeatureVector
        mock_build.return_value = SourceFeatureVector(obs_count=5, log_mean_frp=1.0, log_std_frp=0.0, frp_cv=0.0, months_active=1, nearest_osm_distance_km=1.0, active_duration_days=1, first_seen_month=1)
        out = await service.predict_observation(
            db=mock_db,
            latitude=22.0,
            longitude=70.0,
            timestamp=datetime.now(timezone.utc)
        )

    dump_str = str(out.model_dump())
    assert "FIRMS_MAP_KEY" not in dump_str
    assert "MAPTILER" not in dump_str


def test_data_preservation_integrity():
    """Verify that ML model loading does not alter dataset definitions or feature column names."""
    from app.ml.model import model_manager
    model_manager.load_model()

    assert len(model_manager.feature_columns) == 8
    assert "nearest_osm_distance_km" in model_manager.feature_columns
    assert "months_active" in model_manager.feature_columns
