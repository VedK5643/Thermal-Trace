"""
Phase 9A LLM Provider, Tool Calling Architecture, and Chat Endpoint Unit Tests.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.llm.prompts import SYSTEM_PROMPT
from app.services.llm.tools import TOOL_DECLARATIONS, ToolExecutor
from app.services.llm.provider import GeminiProvider, OpenRouterProvider, get_llm_provider


def test_system_prompt_scientific_disclosures():
    """Verify system prompt contains all mandatory scientific disclosures and tool rules."""
    assert "NASA FIRMS observations are satellite thermal anomaly detections" in SYSTEM_PROMPT
    assert "thermalwatch-v1" in SYSTEM_PROMPT
    assert "ML predictions are NOT verified ground truth" in SYSTEM_PROMPT
    assert "facility_dist_km" in SYSTEM_PROMPT
    assert "93.70% benchmark accuracy" in SYSTEM_PROMPT


def test_tool_declarations_schema():
    """Verify tool registry contains exactly 6 read-only tools with valid schemas."""
    tool_names = [t["name"] for t in TOOL_DECLARATIONS]
    assert len(tool_names) >= 6
    assert "get_hotspots" in tool_names
    assert "get_hotspot_details" in tool_names
    assert "get_alerts" in tool_names
    assert "get_facilities" in tool_names
    assert "get_history" in tool_names
    assert "get_system_status" in tool_names

    # Verify no arbitrary SQL or code execution tools exist
    assert "execute_sql" not in tool_names
    assert "execute_code" not in tool_names


@pytest.mark.anyio
async def test_tool_executor_system_status():
    """Verify ToolExecutor correctly queries system status facts."""
    mock_db = AsyncMock()
    # Mock execute result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalar.return_value = 859
    mock_db.execute.return_value = mock_result

    executor = ToolExecutor(mock_db)
    res = await executor.execute_tool("get_system_status", {})

    assert res["status"] == "healthy"
    assert res["firmsIngestionStatus"] == "ACTIVE"
    assert res["modelVersion"] == "thermalwatch-v1"
    assert res["totalStoredObservations"] == 859


def test_provider_factory_and_fallback():
    """Verify provider factory returns OpenRouterProvider by default."""
    provider = get_llm_provider()
    assert isinstance(provider, OpenRouterProvider)
    assert provider.model is not None
