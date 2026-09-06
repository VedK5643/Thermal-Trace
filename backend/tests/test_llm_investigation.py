"""
Phase 9E Hotspot & Alert Investigation Engine Unit Tests.
Verifies structured evidence retrieval, alert traceability, target isolation rules, missing data abstention, and adversarial investigation protections.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.llm.tools import ToolExecutor
from app.services.llm.prompts import SYSTEM_PROMPT


@pytest.mark.anyio
async def test_tool_executor_hotspot_investigation_evidence():
    """Verify get_hotspot_details retrieves all 5 evidence groups."""
    mock_db = AsyncMock()
    mock_hotspot = MagicMock(
        id="FIRMS-001",
        latitude=19.0760,
        longitude=72.8777,
        type="unknown",
        confidence=85.0,
        ml_type="industrial_thermal_source",
        ml_confidence=0.94,
        model_version="thermalwatch-v1",
        frp=32.5,
        brightness=325.4,
        bright_ti5=298.1,
        satellite="VIIRS_SNPP_NRT",
        severity="high",
        state="Maharashtra",
        persistence_count=5,
        facility_dist_km=1.8,
        facility_id="FAC-001",
        ml_explanation={"bright_ti4": 0.45, "facility_dist_km": 0.30},
        timestamp=MagicMock(isoformat=lambda: "2026-08-26T12:00:00+00:00")
    )

    executor = ToolExecutor(mock_db)
    executor.hotspot_repo.get_by_id = AsyncMock(return_value=mock_hotspot)

    res = await executor.execute_tool("get_hotspot_details", {"hotspot_id": "FIRMS-001"})

    assert res["id"] == "FIRMS-001"
    assert res["mlType"] == "industrial_thermal_source"
    assert res["mlConfidence"] == 0.94
    assert res["frp"] == 32.5
    assert res["persistenceCount"] == 5
    assert res["facilityDistanceKm"] == 1.8
    assert "mlExplanation" in res


@pytest.mark.anyio
async def test_tool_executor_missing_hotspot_id_handling():
    """Verify get_hotspot_details handles non-existent hotspot ID cleanly."""
    mock_db = AsyncMock()
    executor = ToolExecutor(mock_db)
    executor.hotspot_repo.get_by_id = AsyncMock(return_value=None)

    res = await executor.execute_tool("get_hotspot_details", {"hotspot_id": "INVALID-ID"})

    assert "error" in res
    assert "not found" in res["error"]


def test_investigation_prompt_structure_and_rules():
    """Verify system prompt enforces structured investigation sections and target isolation."""
    assert "INVESTIGATION ENGINE & EVIDENCE GROUPING" in SYSTEM_PROMPT
    assert "### Prediction" in SYSTEM_PROMPT
    assert "### Thermal Evidence" in SYSTEM_PROMPT
    assert "### Persistence" in SYSTEM_PROMPT
    assert "### Facility Context" in SYSTEM_PROMPT
    assert "### Alert" in SYSTEM_PROMPT
    assert "### Model Explanation" in SYSTEM_PROMPT
    assert "TARGET SWITCHING" in SYSTEM_PROMPT
    assert "Never mix evidence across targets" in SYSTEM_PROMPT
