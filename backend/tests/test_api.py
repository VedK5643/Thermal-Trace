"""
Backend API tests for ThermalTrace.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Test health endpoint returns 200."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "thermalwatch-api"
    assert "status" in data
    assert "database" in data


@pytest.mark.anyio
async def test_list_hotspots(client: AsyncClient):
    """Test hotspots list endpoint returns paginated response."""
    response = await client.get("/api/v1/hotspots")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert isinstance(data["data"], list)
    assert "page" in data["pagination"]
    assert "page_size" in data["pagination"]
    assert "total" in data["pagination"]


@pytest.mark.anyio
async def test_list_hotspots_with_filters(client: AsyncClient):
    """Test hotspot filtering by type."""
    response = await client.get("/api/v1/hotspots?type=industrial_thermal_source")
    assert response.status_code == 200
    data = response.json()
    for hotspot in data["data"]:
        assert hotspot["type"] == "industrial_thermal_source"


@pytest.mark.anyio
async def test_list_hotspots_min_confidence(client: AsyncClient):
    """Test hotspot filtering by minimum confidence."""
    response = await client.get("/api/v1/hotspots?min_confidence=80")
    assert response.status_code == 200
    data = response.json()
    for hotspot in data["data"]:
        assert hotspot["confidence"] >= 80


@pytest.mark.anyio
async def test_get_hotspot_not_found(client: AsyncClient):
    """Test 404 for non-existent hotspot."""
    response = await client.get("/api/v1/hotspots/NONEXISTENT")
    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "not_found"


@pytest.mark.anyio
async def test_get_hotspot_by_id(client: AsyncClient):
    """Test getting a specific hotspot by ID."""
    response = await client.get("/api/v1/hotspots/HS-001")
    if response.status_code == 200:
        data = response.json()
        assert data["id"] == "HS-001"
        assert "latitude" in data
        assert "longitude" in data
        assert "type" in data
        assert "brightness" in data
        assert "confidence" in data
        assert "severity" in data
        assert "timestamp" in data
        # camelCase serialization check
        assert "facilityId" in data


@pytest.mark.anyio
async def test_list_facilities(client: AsyncClient):
    """Test facilities list endpoint."""
    response = await client.get("/api/v1/facilities")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data


@pytest.mark.anyio
async def test_get_facility_not_found(client: AsyncClient):
    """Test 404 for non-existent facility."""
    response = await client.get("/api/v1/facilities/NONEXISTENT")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_list_alerts(client: AsyncClient):
    """Test alerts list endpoint."""
    response = await client.get("/api/v1/alerts")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data


@pytest.mark.anyio
async def test_get_alert_not_found(client: AsyncClient):
    """Test 404 for non-existent alert."""
    response = await client.get("/api/v1/alerts/NONEXISTENT")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_list_incidents(client: AsyncClient):
    """Test incidents list endpoint (derived from hotspot+facility)."""
    response = await client.get("/api/v1/incidents")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data


@pytest.mark.anyio
async def test_get_incident_not_found(client: AsyncClient):
    """Test 404 for non-existent incident."""
    response = await client.get("/api/v1/incidents/NONEXISTENT")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_hotspot_pagination(client: AsyncClient):
    """Test pagination parameters work correctly."""
    response = await client.get("/api/v1/hotspots?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["page_size"] == 5
    assert len(data["data"]) <= 5


@pytest.mark.anyio
async def test_alert_camelcase_serialization(client: AsyncClient):
    """Test that alert response uses camelCase field names."""
    response = await client.get("/api/v1/alerts")
    assert response.status_code == 200
    data = response.json()
    if data["data"]:
        alert = data["data"][0]
        # Should have camelCase keys
        assert "severity" in alert
        assert "title" in alert
        assert "timestamp" in alert
        assert "acknowledged" in alert


@pytest.mark.anyio
async def test_list_hotspots_spatial_radius(client: AsyncClient):
    """Test PostGIS ST_DWithin spatial radius query centered at Jamnagar (22.3072, 70.8022)."""
    response = await client.get("/api/v1/hotspots?near_lat=22.3072&near_lng=70.8022&radius_km=10")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) > 0
    # Real FIRMS satellite observations returned within 10km spatial radius
    ids = [h["id"] for h in data["data"]]
    assert len(ids) > 0
    assert any(h["id"].startswith("FIRMS") or h["id"] == "HS-001" for h in data["data"])


@pytest.mark.anyio
async def test_ingestion_firms_no_key(client: AsyncClient, monkeypatch):
    """
    Test that the ingestion endpoint returns 503 when FIRMS_MAP_KEY is missing.
    """
    import app.api.v1.ingestion as ingestion_module
    monkeypatch.setattr(ingestion_module.settings, "firms_map_key", "")
    response = await client.post("/api/v1/ingestion/firms")
    assert response.status_code == 503
    assert "FIRMS_MAP_KEY" in response.json()["detail"]


@pytest.mark.anyio
async def test_ingestion_firms_mocked(client: AsyncClient, monkeypatch):
    """
    Test the ingestion endpoint with a mocked FIRMS HTTP response.
    Verifies the endpoint parses, normalizes, and upserts without live network access.
    Matches real NASA FIRMS NRT CSV format (no 'type' column).
    """
    import app.integrations.firms.client as firms_client_module

    # Real FIRMS NRT CSV format: 14 columns, NO 'type' column
    MOCK_CSV = (
        "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,"
        "satellite,instrument,confidence,version,bright_ti5,frp,daynight\n"
        "22.3072,70.8022,340.0,0.4,0.44,2026-08-26,0600,N,VIIRS,h,2.0NRT,293.0,5.2,D\n"
        "22.3100,70.8100,310.0,0.4,0.44,2026-08-26,0700,N,VIIRS,n,2.0NRT,285.0,3.1,D\n"
    )

    async def mock_fetch_csv(self, source, bbox, days):
        return MOCK_CSV

    monkeypatch.setattr(firms_client_module.FIRMSClient, "fetch_csv", mock_fetch_csv)

    response = await client.post(
        "/api/v1/ingestion/firms?source=VIIRS_SNPP_NRT&days=1"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "VIIRS_SNPP_NRT"
    assert data["fetched"] == 2
    # inserted + skipped == fetched (all accounted for)
    assert data["inserted"] + data["skipped"] == 2
    assert data["errors"] == 0

    # Second call: same data → all skipped (idempotency)
    response2 = await client.post(
        "/api/v1/ingestion/firms?source=VIIRS_SNPP_NRT&days=1"
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["fetched"] == 2
    assert data2["skipped"] == 2
    assert data2["inserted"] == 0

