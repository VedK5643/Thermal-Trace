"""
Phase 9G Predictive & Anomaly Intelligence Engine Unit Tests.
Verifies server-side anomaly detection (get_anomalies), minimum sample protection, baseline methodology versioning, forecasting refusal gates, and adversarial predictive safety rules.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.llm.tools import ToolExecutor, TOOL_DECLARATIONS
from app.services.llm.prompts import SYSTEM_PROMPT


def test_predictive_tool_declaration():
    """Verify get_anomalies tool is registered in TOOL_DECLARATIONS."""
    tool_names = [t["name"] for t in TOOL_DECLARATIONS]
    assert "get_anomalies" in tool_names


@pytest.mark.anyio
async def test_tool_executor_get_anomalies_minimum_sample_protection():
    """Verify get_anomalies enforces minimum sample size protection (< 5 observations)."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [MagicMock(), MagicMock()]  # Only 2 observations
    mock_db.execute.return_value = mock_result

    executor = ToolExecutor(mock_db)
    res = await executor.execute_tool("get_anomalies", {"state": "Gujarat"})

    assert res["anomaliesDetected"] is False
    assert res["methodologyVersion"] == "baseline-v1"
    assert "Insufficient historical baseline data" in res["message"]


@pytest.mark.anyio
async def test_tool_executor_get_anomalies_detection():
    """Verify get_anomalies computes statistical deviations and returns structured anomaly categories."""
    mock_db = AsyncMock()

    # Create 6 mock hotspots with high FRP & persistence
    mock_hotspots = [
        MagicMock(frp=42.0, persistence_count=4, ml_type="industrial_thermal_source", state="Maharashtra")
        for _ in range(6)
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_hotspots
    mock_db.execute.return_value = mock_result

    executor = ToolExecutor(mock_db)
    res = await executor.execute_tool("get_anomalies", {"state": "Maharashtra"})

    assert res["anomaliesDetected"] is True
    assert res["methodologyVersion"] == "baseline-v1"
    assert res["anomalyCount"] >= 2
    types = [a["type"] for a in res["detectedAnomalies"]]
    assert "FRP_ANOMALY" in types
    assert "PERSISTENCE_ANOMALY" in types


def test_predictive_safety_prompt_rules():
    """Verify system prompt enforces forecasting refusal gate and forbids fake future probabilities."""
    assert "PREDICTIVE INTELLIGENCE & FORECASTING REFUSAL GATE" in SYSTEM_PROMPT
    assert "ThermalTrace currently does not provide a validated future-fire forecast" in SYSTEM_PROMPT
    assert "NO FAKE PROBABILITIES: Never invent future event probabilities" in SYSTEM_PROMPT
    assert "EARLY WARNING LANGUAGE" in SYSTEM_PROMPT
    assert "ANOMALY CATEGORIES: ACTIVITY_SPIKE, FRP_ANOMALY, PERSISTENCE_ANOMALY" in SYSTEM_PROMPT
