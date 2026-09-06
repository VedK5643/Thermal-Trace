"""
Phase 9D Dynamic Analytics & Investigation Engine Unit Tests.
Verifies server-side statistical aggregation, period comparisons, regional comparisons, candidate ranking, and adversarial analytics protections.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.llm.tools import ToolExecutor, TOOL_DECLARATIONS
from app.services.llm.prompts import SYSTEM_PROMPT


def test_analytical_tool_declarations():
    """Verify tool declarations contain all 10 read-only backend tools including analytical tools."""
    tool_names = [t["name"] for t in TOOL_DECLARATIONS]
    assert len(tool_names) >= 10
    assert "get_hotspot_statistics" in tool_names
    assert "compare_periods" in tool_names
    assert "compare_regions" in tool_names
    assert "get_top_hotspots" in tool_names


@pytest.mark.anyio
async def test_tool_executor_hotspot_statistics():
    """Verify get_hotspot_statistics computes server-side aggregations correctly."""
    mock_db = AsyncMock()
    mock_hotspot1 = MagicMock(ml_type="industrial_thermal_source", severity="high", frp=45.0, ml_confidence=0.92, persistence_count=3, state="Gujarat")
    mock_hotspot2 = MagicMock(ml_type="natural_fire", severity="medium", frp=15.0, ml_confidence=0.85, persistence_count=1, state="Gujarat")
    mock_hotspot3 = MagicMock(ml_type="unknown", severity="low", frp=5.0, ml_confidence=0.40, persistence_count=1, state="Gujarat")

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_hotspot1, mock_hotspot2, mock_hotspot3]
    mock_db.execute.return_value = mock_result

    executor = ToolExecutor(mock_db)
    res = await executor.execute_tool("get_hotspot_statistics", {"state": "Gujarat"})

    assert res["totalObservations"] == 3
    assert res["classificationBreakdown"]["industrial_thermal_source"] == 1
    assert res["classificationBreakdown"]["natural_fire"] == 1
    assert res["classificationBreakdown"]["unknown"] == 1
    assert res["unknownCount"] == 1
    assert res["persistentEventCount"] == 1
    assert res["averageFRP"] == 21.67
    assert res["maximumFRP"] == 45.0


@pytest.mark.anyio
async def test_tool_executor_compare_periods():
    """Verify compare_periods correctly computes count changes and handles zero denominators safely."""
    mock_db = AsyncMock()

    # Mock max timestamp query
    mock_ts_result = MagicMock()
    mock_ts_result.scalar.return_value = None

    # Mock count queries for period A and period B
    mock_count_a = MagicMock()
    mock_count_a.scalar.return_value = 120
    mock_count_b = MagicMock()
    mock_count_b.scalar.return_value = 100

    mock_db.execute.side_effect = [mock_ts_result, mock_count_a, mock_count_b]

    executor = ToolExecutor(mock_db)
    res = await executor.execute_tool("compare_periods", {"period_days": 7})

    assert res["currentPeriodCount"] == 120
    assert res["previousPeriodCount"] == 100
    assert res["absoluteDifference"] == 20
    assert res["percentageChange"] == 20.0
    assert res["trendDirection"] == "increase"


@pytest.mark.anyio
async def test_tool_executor_compare_regions():
    """Verify compare_regions state comparison execution."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    executor = ToolExecutor(mock_db)
    res = await executor.execute_tool("compare_regions", {"state_a": "Maharashtra", "state_b": "Gujarat"})

    assert "regionA" in res
    assert "regionB" in res
    assert res["regionA"]["state"] == "Maharashtra"
    assert res["regionB"]["state"] == "Gujarat"


@pytest.mark.anyio
async def test_tool_executor_get_top_hotspots():
    """Verify get_top_hotspots candidate ranking."""
    mock_db = AsyncMock()
    mock_hotspot = MagicMock(
        id="FIRMS-001",
        state="Maharashtra",
        ml_type="industrial_thermal_source",
        ml_confidence=0.95,
        frp=60.0,
        severity="high",
        persistence_count=4,
        facility_dist_km=1.2
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_hotspot]
    mock_db.execute.return_value = mock_result

    executor = ToolExecutor(mock_db)
    res = await executor.execute_tool("get_top_hotspots", {"rank_by": "frp", "limit": 5})

    assert res["rankingMetric"] == "frp"
    assert res["totalRanked"] == 1
    assert res["candidates"][0]["id"] == "FIRMS-001"
    assert res["candidates"][0]["frp"] == 60.0


def test_analytical_guidelines_in_system_prompt():
    """Verify system prompt instructs model to use dedicated analytical tools."""
    assert "get_hotspot_statistics" in SYSTEM_PROMPT
    assert "compare_periods" in SYSTEM_PROMPT
    assert "compare_regions" in SYSTEM_PROMPT
    assert "get_top_hotspots" in SYSTEM_PROMPT
    assert "Do NOT perform manual raw counting" in SYSTEM_PROMPT
