"""
Phase 5D tests: multi-source FIRMS ingestion coverage enhancement.

Tests cover:
  - Multiple FIRMS sources ingest correctly (SNPP, NOAA-20, NOAA-21)
  - Same-source duplicate is skipped (idempotency)
  - Same lat/lon/time but different SOURCE → different ID → separate records
  - Partial source failure isolation (one source raises, others succeed)
  - Empty source response is handled gracefully
  - Source traceability: each record has correct source field
  - All ingested records default to type='unknown' (no ML classification)
  - India bbox constraint: observations outside India are filtered
  - Multi-source summary structure is correct
  - API endpoint /ingestion/firms/all structure
  - Config: firms_source_list and firms_ingestion_days defaults
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient

from app.main import app
from app.integrations.firms.normalizer import parse_firms_csv, _make_stable_id
from app.core.config import settings


# ─── CSV fixtures ────────────────────────────────────────────────────────────

# Real FIRMS NRT header (no type column)
VIIRS_HEADER = (
    "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,"
    "satellite,instrument,confidence,version,bright_ti5,frp,daynight"
)

def _row(lat, lon, date="2026-08-22", time="0600", conf="h", brightness="330.0", frp="4.5"):
    return f"{lat},{lon},{brightness},0.4,0.44,{date},{time},N,VIIRS,{conf},2.0NRT,290.0,{frp},D"

# India coordinates
JAMNAGAR   = (22.3072, 70.8022)
DELHI      = (28.6139, 77.2090)
CHENNAI    = (13.0827, 80.2707)
DIBRUGARH  = (27.4728, 94.9120)  # Assam (far east)
LEH        = (34.1526, 77.5771)  # Ladakh (far north)

# Outside India
SRI_LANKA  = (6.9271, 79.8612)
KATHMANDU  = (27.7172, 85.3240)  # Nepal


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ─── Unit: stable ID distinguishes different sources ─────────────────────────

class TestStableIdPerSource:
    def test_same_source_same_observation_gives_same_id(self):
        """Idempotency: re-ingesting same observation from same source → same ID."""
        id1 = _make_stable_id("VIIRS_SNPP_NRT", 22.3072, 70.8022, "2026-08-22", "0600")
        id2 = _make_stable_id("VIIRS_SNPP_NRT", 22.3072, 70.8022, "2026-08-22", "0600")
        assert id1 == id2

    def test_different_source_same_observation_gives_different_id(self):
        """Two legitimate satellites detecting the same fire → two separate records."""
        id_snpp   = _make_stable_id("VIIRS_SNPP_NRT",   22.3072, 70.8022, "2026-08-22", "0600")
        id_noaa20 = _make_stable_id("VIIRS_NOAA20_NRT", 22.3072, 70.8022, "2026-08-22", "0600")
        id_noaa21 = _make_stable_id("VIIRS_NOAA21_NRT", 22.3072, 70.8022, "2026-08-22", "0600")
        assert id_snpp != id_noaa20
        assert id_snpp != id_noaa21
        assert id_noaa20 != id_noaa21

    def test_different_time_same_source_gives_different_id(self):
        id1 = _make_stable_id("VIIRS_SNPP_NRT", 22.3072, 70.8022, "2026-08-22", "0600")
        id2 = _make_stable_id("VIIRS_SNPP_NRT", 22.3072, 70.8022, "2026-08-22", "0700")
        assert id1 != id2

    def test_different_date_same_source_gives_different_id(self):
        id1 = _make_stable_id("VIIRS_SNPP_NRT", 22.3072, 70.8022, "2026-08-21", "0600")
        id2 = _make_stable_id("VIIRS_SNPP_NRT", 22.3072, 70.8022, "2026-08-22", "0600")
        assert id1 != id2


# ─── Unit: multi-source normalization ────────────────────────────────────────

class TestMultiSourceNormalization:
    def _make_csv(self, lat, lon, date="2026-08-22", time="0600"):
        return f"{VIIRS_HEADER}\n{_row(lat, lon, date, time)}"

    def test_snpp_source_traceability(self):
        records = parse_firms_csv(self._make_csv(*JAMNAGAR), "VIIRS_SNPP_NRT")
        assert len(records) == 1
        assert records[0]["source"] == "VIIRS_SNPP_NRT"

    def test_noaa20_source_traceability(self):
        records = parse_firms_csv(self._make_csv(*JAMNAGAR), "VIIRS_NOAA20_NRT")
        assert len(records) == 1
        assert records[0]["source"] == "VIIRS_NOAA20_NRT"

    def test_noaa21_source_traceability(self):
        records = parse_firms_csv(self._make_csv(*JAMNAGAR), "VIIRS_NOAA21_NRT")
        assert len(records) == 1
        assert records[0]["source"] == "VIIRS_NOAA21_NRT"

    def test_all_real_source_records_type_unknown(self):
        """Real FIRMS NRT has no type column → type should default to unknown."""
        for source in ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT"]:
            records = parse_firms_csv(self._make_csv(*DELHI), source)
            assert len(records) == 1
            assert records[0]["type"] == "unknown", (
                f"Source {source}: type must be 'unknown' for real NRT data"
            )

    def test_india_wide_coverage_coordinates_all_accepted(self):
        """Verify observations from extreme corners of India are all accepted."""
        corners = [JAMNAGAR, DELHI, CHENNAI, DIBRUGARH, LEH]
        for lat, lon in corners:
            records = parse_firms_csv(self._make_csv(lat, lon), "VIIRS_SNPP_NRT")
            assert len(records) == 1, f"Expected observation at ({lat}, {lon}) to be accepted"

    def test_outside_india_coordinates_rejected(self):
        """Observations from neighboring countries must be filtered out."""
        for lat, lon in [SRI_LANKA, KATHMANDU]:
            records = parse_firms_csv(self._make_csv(lat, lon), "VIIRS_SNPP_NRT")
            assert len(records) == 0, f"Expected ({lat}, {lon}) to be rejected"

    def test_multi_day_rows_all_accepted(self):
        """Rows from 5 different dates all normalize correctly."""
        dates = ["2026-08-18", "2026-08-19", "2026-08-20", "2026-08-21", "2026-08-22"]
        rows = "\n".join(_row(*DELHI, date=d) for d in dates)
        csv_text = f"{VIIRS_HEADER}\n{rows}"
        records = parse_firms_csv(csv_text, "VIIRS_SNPP_NRT")
        assert len(records) == 5

    def test_multi_source_same_location_give_unique_ids(self):
        """Two satellites at same location → distinct IDs → two DB records allowed."""
        lat, lon = JAMNAGAR
        csv_text = f"{VIIRS_HEADER}\n{_row(lat, lon)}"
        r_snpp   = parse_firms_csv(csv_text, "VIIRS_SNPP_NRT")[0]
        r_noaa20 = parse_firms_csv(csv_text, "VIIRS_NOAA20_NRT")[0]
        assert r_snpp["id"] != r_noaa20["id"]

    def test_empty_csv_returns_empty(self):
        records = parse_firms_csv("", "VIIRS_NOAA20_NRT")
        assert records == []

    def test_header_only_returns_empty(self):
        records = parse_firms_csv(VIIRS_HEADER, "VIIRS_NOAA21_NRT")
        assert records == []

    def test_invalid_lat_lon_skipped(self):
        bad_row = "not_a_number,also_bad,330.0,0.4,0.44,2026-08-22,0600,N,VIIRS,h,2.0NRT,290.0,4.5,D"
        csv_text = f"{VIIRS_HEADER}\n{bad_row}"
        records = parse_firms_csv(csv_text, "VIIRS_SNPP_NRT")
        assert records == []

    def test_zero_brightness_skipped(self):
        bad_row = _row(*JAMNAGAR, brightness="0.0")
        csv_text = f"{VIIRS_HEADER}\n{bad_row}"
        records = parse_firms_csv(csv_text, "VIIRS_SNPP_NRT")
        assert records == []

    def test_error_json_response_returns_empty(self):
        records = parse_firms_csv('{"error": "invalid key"}', "VIIRS_SNPP_NRT")
        assert records == []


# ─── Integration: API endpoint (mocked HTTP) ─────────────────────────────────

@pytest.mark.anyio
async def test_firms_single_source_endpoint_uses_default_days(client: AsyncClient, monkeypatch):
    """POST /ingestion/firms with no days param uses settings.firms_ingestion_days."""
    import app.integrations.firms.client as firms_client_module

    MOCK_CSV = f"{VIIRS_HEADER}\n{_row(*JAMNAGAR)}\n{_row(*DELHI)}"

    calls = []
    async def mock_fetch_csv(self, source, bbox, days):
        calls.append({"source": source, "days": days})
        return MOCK_CSV

    monkeypatch.setattr(firms_client_module.FIRMSClient, "fetch_csv", mock_fetch_csv)

    response = await client.post("/api/v1/ingestion/firms?source=VIIRS_SNPP_NRT")
    assert response.status_code == 200
    # days should match configured default (5)
    assert calls[0]["days"] == settings.firms_ingestion_days


@pytest.mark.anyio
async def test_firms_all_sources_endpoint_basic_structure(client: AsyncClient, monkeypatch):
    """POST /ingestion/firms/all returns the correct multi-source summary structure."""
    import app.integrations.firms.client as firms_client_module

    MOCK_CSV = f"{VIIRS_HEADER}\n{_row(*JAMNAGAR)}\n{_row(*DELHI)}"

    async def mock_fetch_csv(self, source, bbox, days):
        return MOCK_CSV

    monkeypatch.setattr(firms_client_module.FIRMSClient, "fetch_csv", mock_fetch_csv)

    response = await client.post("/api/v1/ingestion/firms/all")
    assert response.status_code == 200
    data = response.json()

    # Required top-level keys
    assert "sources_attempted" in data
    assert "sources_succeeded" in data
    assert "sources_failed" in data
    assert "total_fetched" in data
    assert "total_inserted" in data
    assert "total_skipped" in data
    assert "bbox" in data
    assert "days" in data
    assert "per_source" in data
    assert "errors" in data

    # All 3 configured sources should be attempted
    assert data["sources_attempted"] == 3
    assert data["sources_succeeded"] == 3
    assert data["sources_failed"] == 0
    assert isinstance(data["per_source"], list)
    assert len(data["per_source"]) == 3


@pytest.mark.anyio
async def test_firms_all_sources_failure_isolation(client: AsyncClient, monkeypatch):
    """
    If one FIRMS source raises an exception, the other sources still succeed.
    The endpoint must return 200 (not 502) with partial results.
    """
    import app.integrations.firms.client as firms_client_module

    MOCK_CSV = f"{VIIRS_HEADER}\n{_row(*JAMNAGAR)}"
    call_count = [0]

    async def mock_fetch_csv_partial_failure(self, source, bbox, days):
        call_count[0] += 1
        if source == "VIIRS_NOAA21_NRT":
            raise RuntimeError("Simulated NOAA-21 API timeout")
        return MOCK_CSV

    monkeypatch.setattr(
        firms_client_module.FIRMSClient, "fetch_csv", mock_fetch_csv_partial_failure
    )

    response = await client.post("/api/v1/ingestion/firms/all")
    assert response.status_code == 200  # 200, not 502 — partial success is OK
    data = response.json()

    # One source failed, two succeeded
    assert data["sources_attempted"] == 3
    assert data["sources_succeeded"] == 2
    assert data["sources_failed"] == 1
    assert len(data["errors"]) == 1
    assert data["errors"][0]["source"] == "VIIRS_NOAA21_NRT"
    assert "NOAA-21" in data["errors"][0]["error"]

    # Successful sources still have data
    assert data["total_fetched"] > 0


@pytest.mark.anyio
async def test_firms_all_sources_idempotency(client: AsyncClient, monkeypatch):
    """Calling /ingestion/firms/all twice → second call has all records skipped."""
    import app.integrations.firms.client as firms_client_module

    MOCK_CSV = f"{VIIRS_HEADER}\n{_row(*JAMNAGAR, time='0500')}\n{_row(*DELHI, time='0500')}"

    async def mock_fetch_csv(self, source, bbox, days):
        return MOCK_CSV

    monkeypatch.setattr(firms_client_module.FIRMSClient, "fetch_csv", mock_fetch_csv)

    # First call — inserts records
    r1 = await client.post("/api/v1/ingestion/firms/all")
    assert r1.status_code == 200
    d1 = r1.json()
    first_inserted = d1["total_inserted"]

    # Second call — all already exist → all skipped
    r2 = await client.post("/api/v1/ingestion/firms/all")
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["total_inserted"] == 0
    assert d2["total_skipped"] == d2["total_fetched"]


@pytest.mark.anyio
async def test_firms_all_empty_source_response(client: AsyncClient, monkeypatch):
    """An empty FIRMS response (header-only) results in fetched=0, not an error."""
    import app.integrations.firms.client as firms_client_module

    async def mock_fetch_csv_empty(self, source, bbox, days):
        return VIIRS_HEADER  # header only, no data rows

    monkeypatch.setattr(
        firms_client_module.FIRMSClient, "fetch_csv", mock_fetch_csv_empty
    )

    response = await client.post("/api/v1/ingestion/firms/all")
    assert response.status_code == 200
    data = response.json()
    assert data["total_fetched"] == 0
    assert data["total_inserted"] == 0
    assert data["sources_failed"] == 0  # empty is not a failure


@pytest.mark.anyio
async def test_firms_all_no_key_returns_503(client: AsyncClient, monkeypatch):
    """POST /ingestion/firms/all returns 503 when FIRMS_MAP_KEY is not set."""
    import app.api.v1.ingestion as ingestion_module
    monkeypatch.setattr(ingestion_module.settings, "firms_map_key", "")
    response = await client.post("/api/v1/ingestion/firms/all")
    assert response.status_code == 503
    assert "FIRMS_MAP_KEY" in response.json()["detail"]


@pytest.mark.anyio
async def test_firms_all_custom_sources_param(client: AsyncClient, monkeypatch):
    """POST /ingestion/firms/all?sources=VIIRS_SNPP_NRT only ingests SNPP."""
    import app.integrations.firms.client as firms_client_module

    ingested_sources = []

    async def mock_fetch_csv(self, source, bbox, days):
        ingested_sources.append(source)
        return VIIRS_HEADER  # empty

    monkeypatch.setattr(firms_client_module.FIRMSClient, "fetch_csv", mock_fetch_csv)

    response = await client.post(
        "/api/v1/ingestion/firms/all?sources=VIIRS_SNPP_NRT"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sources_attempted"] == 1
    assert ingested_sources == ["VIIRS_SNPP_NRT"]


# ─── Config tests ─────────────────────────────────────────────────────────────

class TestPhase5DConfig:
    def test_firms_ingestion_days_default(self):
        assert settings.firms_ingestion_days == 5

    def test_firms_source_list_default(self):
        src = settings.firms_source_list
        assert "VIIRS_SNPP_NRT" in src
        assert "VIIRS_NOAA20_NRT" in src
        assert "VIIRS_NOAA21_NRT" in src
        assert len(src) == 3

    def test_firms_source_list_no_empty_strings(self):
        for s in settings.firms_source_list:
            assert s.strip() != ""
