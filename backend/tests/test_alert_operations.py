"""
Phase 7B Operational Alert Quality & Deduplication Unit Tests.
Verifies multi-factor severity prioritization, false positive protection, and idempotent deduplication.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.services.alert import AlertService
from app.db.models.alert import Alert


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def alert_service(mock_db):
    service = AlertService(mock_db)
    service.repo.get_by_hotspot_id = AsyncMock(return_value=None)
    service.repo.create = AsyncMock(side_effect=lambda alert: alert)
    return service


@pytest.mark.anyio
async def test_multi_factor_critical_industrial_alert(alert_service):
    """Verify Critical severity for high-confidence industrial thermal source near facility with high FRP."""
    hotspot = MagicMock()
    hotspot.id = "FIRMS-test-critical-01"
    hotspot.facility_id = "FAC-gujarat-001"
    hotspot.ml_type = "industrial_thermal_source"
    hotspot.ml_confidence = 0.88
    hotspot.frp = 28.5
    hotspot.facility_dist_km = 2.1
    hotspot.persistence_count = 5
    hotspot.timestamp = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)

    alert = await alert_service.evaluate_hotspot_alert(hotspot)
    assert alert is not None
    assert alert.severity == "critical"
    assert "Critical Industrial Thermal Event near Facility" in alert.title
    assert "28.5" in alert.message


@pytest.mark.anyio
async def test_false_positive_protection_wildfire_near_facility(alert_service):
    """Verify that a wildfire near a facility is NOT falsely flagged as an Industrial Thermal Source alert."""
    hotspot = MagicMock()
    hotspot.id = "FIRMS-test-wildfire-02"
    hotspot.facility_id = "FAC-forest-002"
    hotspot.ml_type = "natural_fire"
    hotspot.ml_confidence = 0.94
    hotspot.frp = 35.0
    hotspot.facility_dist_km = 1.2
    hotspot.persistence_count = 4
    hotspot.timestamp = datetime(2026, 8, 26, 14, 0, tzinfo=timezone.utc)

    alert = await alert_service.evaluate_hotspot_alert(hotspot)
    # High confidence natural fire near facility triggers Medium persistent anomaly alert, NOT Critical Industrial Event
    assert alert is not None
    assert alert.severity in ("medium", "low")
    assert "Industrial Thermal Event" not in alert.title


@pytest.mark.anyio
async def test_alert_idempotent_deduplication(alert_service):
    """Verify that repeated evaluation of the same hotspot does NOT produce duplicate alerts."""
    hotspot = MagicMock()
    hotspot.id = "FIRMS-test-dup-03"
    hotspot.ml_type = "industrial_thermal_source"
    hotspot.ml_confidence = 0.82
    hotspot.frp = 22.0
    hotspot.facility_dist_km = 3.0
    hotspot.persistence_count = 3
    hotspot.timestamp = datetime(2026, 8, 26, 15, 0, tzinfo=timezone.utc)

    # First evaluation creates alert
    alert1 = await alert_service.evaluate_hotspot_alert(hotspot)
    assert alert1 is not None

    # Simulate existing alert in repo
    alert_service.repo.get_by_hotspot_id = AsyncMock(return_value=alert1)

    # Second evaluation returns None (deduplicated)
    alert2 = await alert_service.evaluate_hotspot_alert(hotspot)
    assert alert2 is None
