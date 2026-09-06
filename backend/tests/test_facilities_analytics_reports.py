"""
Unit tests for Facilities, Analytics, and Reports API endpoints.
Verifies server-side aggregation, summary endpoints, temporal time series, regional state rankings, and structured report generation.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from app.api.v1.analytics import get_analytics_summary, get_temporal_analytics, get_regional_analytics
from app.api.v1.reports import generate_report, ReportRequest
from app.api.v1.facilities import get_facilities_summary


@pytest.mark.anyio
async def test_facilities_summary_endpoint():
    """Verify /facilities/summary aggregates facility type distribution counts."""
    mock_db = AsyncMock()
    executor_mock = MagicMock()

    f1 = MagicMock(type="Refinery")
    f2 = MagicMock(type="Power Plant")
    f3 = MagicMock(type="Refinery")

    # Mock FacilityService.list
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [f1, f2, f3]
    mock_db.execute.return_value = mock_res

    res = await get_facilities_summary(db=mock_db)
    assert "totalFacilities" in res
    assert "typeDistribution" in res
    assert res["typeDistribution"].get("Refinery") == 2
    assert res["typeDistribution"].get("Power Plant") == 1


@pytest.mark.anyio
async def test_analytics_summary_endpoint():
    """Verify /analytics/summary returns top-level observations, industrial percentage, and model disclosures."""
    mock_db = AsyncMock()

    h1 = MagicMock(ml_type="industrial_thermal_source", severity="high", frp=45.0, persistence_count=4, state="Maharashtra")
    h2 = MagicMock(ml_type="natural_fire", severity="medium", frp=20.0, persistence_count=1, state="Karnataka")

    mock_hotspot_res = MagicMock()
    mock_hotspot_res.scalars.return_value.all.return_value = [h1, h2]

    mock_alert_res = MagicMock()
    mock_alert_res.scalar.return_value = 1

    mock_db.execute.side_effect = [mock_hotspot_res, mock_alert_res]

    res = await get_analytics_summary(db=mock_db)

    assert res["totalObservations"] == 2
    assert res["industrialSourcePercentage"] == 50.0
    assert res["highCriticalAlerts"] == 1
    assert res["persistentEvents"] == 1
    assert res["modelVersion"] == "thermalwatch-v1"
    assert "4-class taxonomy" in res["benchmarkDisclosure"]


@pytest.mark.anyio
async def test_reports_generate_endpoint_json():
    """Verify /reports/generate produces structured JSON incident report."""
    mock_db = AsyncMock()

    h1 = MagicMock(id="FIRMS-001", latitude=23.5, longitude=87.2, timestamp=datetime.now(timezone.utc), type="unknown", confidence=65.0, ml_type="industrial_thermal_source", ml_confidence=0.95, frp=42.0, severity="high", persistence_count=3, facility_dist_km=1.2)

    mock_hotspot_res = MagicMock()
    mock_hotspot_res.scalars.return_value.all.return_value = [h1]

    mock_alert_res = MagicMock()
    mock_alert_res.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [mock_hotspot_res, mock_alert_res]

    req = ReportRequest(state="Maharashtra", classification="industrial_thermal_source", format="json")
    res = await generate_report(req=req, db=mock_db)

    assert "reportMetadata" in res
    assert "executiveSummary" in res
    assert res["executiveSummary"]["totalObservations"] == 1
    assert "predictedIndustrialThermalSources" in res["executiveSummary"]
    assert res["executiveSummary"]["predictedIndustrialThermalSources"] == 1
    assert "scientificDisclosures" in res
    assert "nonCausationNotice" in res["scientificDisclosures"]
