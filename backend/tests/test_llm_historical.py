"""
Phase 9F Historical & Comparative Intelligence Engine Unit Tests.
Verifies observation vs event count distinctions, period comparison calculations, zero-denominator safety, small-sample warnings, data gap disclosures, and model version awareness.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.llm.tools import ToolExecutor
from app.services.llm.prompts import SYSTEM_PROMPT


@pytest.mark.anyio
async def test_tool_executor_get_history_observation_vs_event():
    """Verify get_history distinguishes observationCount from uniqueEventCount and includes modelVersion."""
    mock_db = AsyncMock()
    mock_count_res = MagicMock()
    mock_count_res.scalar.return_value = 100

    mock_group_res = MagicMock()
    mock_group_res.all.return_value = [("industrial_thermal_source", 30), ("natural_fire", 70)]

    mock_db.execute.side_effect = [mock_count_res, mock_group_res]

    executor = ToolExecutor(mock_db)
    res = await executor.execute_tool("get_history", {})

    assert res["observationCount"] == 100
    assert res["uniqueEventCount"] == 72
    assert res["modelVersion"] == "thermalwatch-v1"
    assert "classificationDistribution" in res


@pytest.mark.anyio
async def test_tool_executor_compare_periods_zero_denominator_safety():
    """Verify compare_periods handles zero previous period count safely without division by zero errors."""
    mock_db = AsyncMock()

    mock_ts_result = MagicMock()
    mock_ts_result.scalar.return_value = None

    mock_count_a = MagicMock()
    mock_count_a.scalar.return_value = 15
    mock_count_b = MagicMock()
    mock_count_b.scalar.return_value = 0

    mock_db.execute.side_effect = [mock_ts_result, mock_count_a, mock_count_b]

    executor = ToolExecutor(mock_db)
    res = await executor.execute_tool("compare_periods", {"period_days": 7})

    assert res["currentPeriodCount"] == 15
    assert res["previousPeriodCount"] == 0
    assert res["percentageChange"] == 100.0
    assert res["trendDirection"] == "increase"


def test_historical_prompt_rules_and_structure():
    """Verify system prompt includes observation vs event distinction and comparison output formatting."""
    assert "OBSERVATION VS EVENT DISTINCTION" in SYSTEM_PROMPT
    assert "HISTORICAL & COMPARATIVE INTELLIGENCE" in SYSTEM_PROMPT
    assert "### Period A" in SYSTEM_PROMPT
    assert "### Period B" in SYSTEM_PROMPT
    assert "### Change" in SYSTEM_PROMPT
    assert "### Interpretation" in SYSTEM_PROMPT
    assert "ZERO-DENOMINATOR RULE" in SYSTEM_PROMPT
    assert "SMALL-SAMPLE WARNING" in SYSTEM_PROMPT
    assert "DATA GAP DISCLOSURE" in SYSTEM_PROMPT
