"""
Unit tests for the FIRMS normalizer.
These tests are pure Python — no database, no HTTP calls.
"""
import pytest
from datetime import datetime, timezone

from app.integrations.firms.normalizer import (
    parse_firms_csv,
    _make_stable_id,
    _derive_severity,
    classify_india_hotspot,
    is_inside_india,
)


# ─── Helper: build a minimal VIIRS CSV ───────────────────────────────────────

# VIIRS header WITH type column (for tests that explicitly test type mapping)
VIIRS_HEADER = (
    "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,"
    "satellite,instrument,confidence,version,bright_ti5,frp,daynight,type"
)

# VIIRS header WITHOUT type column (matches the real NASA FIRMS NRT API response)
VIIRS_HEADER_REAL = (
    "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,"
    "satellite,instrument,confidence,version,bright_ti5,frp,daynight"
)

def _viirs_row(
    lat="22.3072",
    lon="70.8022",
    brightness="340.0",
    acq_date="2026-08-26",
    acq_time="0630",
    confidence="h",
    fire_type="0",
    frp="5.2",
):
    return (
        f"{lat},{lon},{brightness},0.4,0.44,{acq_date},{acq_time},"
        f"N,VIIRS,{confidence},2.0NRT,293.0,{frp},D,{fire_type}"
    )

def _viirs_row_real(
    lat="22.3072",
    lon="70.8022",
    brightness="340.0",
    acq_date="2026-08-26",
    acq_time="0630",
    confidence="h",
    frp="5.2",
):
    """Row matching the real FIRMS NRT API format (no type column)."""
    return (
        f"{lat},{lon},{brightness},0.4,0.44,{acq_date},{acq_time},"
        f"N,VIIRS,{confidence},2.0NRT,293.0,{frp},D"
    )


MODIS_HEADER = (
    "latitude,longitude,brightness,scan,track,acq_date,acq_time,"
    "satellite,instrument,confidence,version,bright_t31,frp,daynight,type"
)

def _modis_row(
    lat="22.3072",
    lon="70.8022",
    brightness="340.0",
    acq_date="2026-08-26",
    acq_time="0630",
    confidence="85",
    fire_type="3",
    frp="5.2",
):
    return (
        f"{lat},{lon},{brightness},1.0,1.0,{acq_date},{acq_time},"
        f"Terra,MODIS,{confidence},6.1NRT,293.0,{frp},D,{fire_type}"
    )


# ─── Tests ───────────────────────────────────────────────────────────────────

class TestMakeStableId:
    def test_deterministic(self):
        id1 = _make_stable_id("VIIRS_SNPP_NRT", 22.3072, 70.8022, "2026-08-26", "0630")
        id2 = _make_stable_id("VIIRS_SNPP_NRT", 22.3072, 70.8022, "2026-08-26", "0630")
        assert id1 == id2

    def test_different_inputs_give_different_ids(self):
        id1 = _make_stable_id("VIIRS_SNPP_NRT", 22.3072, 70.8022, "2026-08-26", "0630")
        id2 = _make_stable_id("VIIRS_SNPP_NRT", 22.3072, 70.8022, "2026-08-26", "0700")
        assert id1 != id2

    def test_prefix(self):
        id1 = _make_stable_id("VIIRS_SNPP_NRT", 22.3072, 70.8022, "2026-08-26", "0630")
        assert id1.startswith("FIRMS-")


class TestDeriveSeverity:
    def test_critical(self):
        assert _derive_severity(345.0, 90.0) == "critical"

    def test_high(self):
        assert _derive_severity(325.0, 75.0) == "high"

    def test_low(self):
        assert _derive_severity(250.0, 40.0) == "low"


class TestIsInsideIndia:
    def test_indian_coordinates(self):
        assert is_inside_india(22.3072, 70.8022) is True  # Jamnagar
        assert is_inside_india(13.0827, 80.2707) is True  # Chennai
        assert is_inside_india(34.1526, 77.5771) is True  # Leh
        assert is_inside_india(11.6233, 92.7265) is True  # Andaman

    def test_foreign_coordinates(self):
        assert is_inside_india(6.9271, 79.8612) is False   # Sri Lanka
        assert is_inside_india(31.5204, 74.3587) is False  # Pakistan
        assert is_inside_india(27.7172, 85.3240) is False  # Nepal
        assert is_inside_india(23.8103, 90.4125) is False  # Bangladesh


class TestParseVIIRSCsv:
    def test_parses_single_viirs_row(self):
        csv_text = f"{VIIRS_HEADER}\n{_viirs_row()}"
        records = parse_firms_csv(csv_text, "VIIRS_SNPP_NRT")
        assert len(records) == 1
        r = records[0]
        assert r["latitude"] == pytest.approx(22.3072)
        assert r["longitude"] == pytest.approx(70.8022)
        assert r["brightness"] == pytest.approx(340.0)
        assert r["confidence"] == 90.0   # 'h' → 90
        assert r["type"] == "unknown"    # always unknown now
        assert r["status"] == "active"
        assert r["country"] == "India"
        assert r["source"] == "VIIRS_SNPP_NRT"  # source traceability
        assert isinstance(r["timestamp"], datetime)
        assert r["frp"] == pytest.approx(5.2)

    def test_real_firms_format_no_type_column_defaults_to_unknown(self):
        """CRITICAL: Real NASA FIRMS NRT responses have no 'type' column.
        The normalizer must default to 'unknown', NOT 'natural_fire'."""
        csv_text = f"{VIIRS_HEADER_REAL}\n{_viirs_row_real()}"
        records = parse_firms_csv(csv_text, "VIIRS_SNPP_NRT")
        assert len(records) == 1
        r = records[0]
        # Real NRT data missing 'type' column should always be 'unknown'
        assert r["type"] == "unknown", (
            f"Expected 'unknown' for missing type column, got '{r['type']}'."
        )
        assert r["source"] == "VIIRS_SNPP_NRT"

    def test_source_field_set_correctly(self):
        csv_text = f"{VIIRS_HEADER}\n{_viirs_row()}"
        records = parse_firms_csv(csv_text, "VIIRS_SNPP_NRT")
        assert records[0]["source"] == "VIIRS_SNPP_NRT"

    def test_viirs_low_confidence_maps_to_30(self):
        csv_text = f"{VIIRS_HEADER}\n{_viirs_row(confidence='l')}"
        records = parse_firms_csv(csv_text, "VIIRS_SNPP_NRT")
        assert records[0]["confidence"] == 30.0

    def test_viirs_nominal_confidence_maps_to_65(self):
        csv_text = f"{VIIRS_HEADER}\n{_viirs_row(confidence='n')}"
        records = parse_firms_csv(csv_text, "VIIRS_SNPP_NRT")
        assert records[0]["confidence"] == 65.0

    def test_empty_csv_returns_empty_list(self):
        records = parse_firms_csv("", "VIIRS_SNPP_NRT")
        assert records == []

    def test_header_only_returns_empty_list(self):
        records = parse_firms_csv(VIIRS_HEADER, "VIIRS_SNPP_NRT")
        assert records == []

    def test_id_is_stable_across_calls(self):
        csv_text = f"{VIIRS_HEADER}\n{_viirs_row()}"
        r1 = parse_firms_csv(csv_text, "VIIRS_SNPP_NRT")[0]
        r2 = parse_firms_csv(csv_text, "VIIRS_SNPP_NRT")[0]
        assert r1["id"] == r2["id"]

    def test_multiple_rows(self):
        rows = "\n".join([_viirs_row(acq_time=str(t)) for t in range(600, 610)])
        csv_text = f"{VIIRS_HEADER}\n{rows}"
        records = parse_firms_csv(csv_text, "VIIRS_SNPP_NRT")
        assert len(records) == 10

    def test_timestamp_is_utc(self):
        csv_text = f"{VIIRS_HEADER}\n{_viirs_row(acq_date='2026-08-26', acq_time='0630')}"
        r = parse_firms_csv(csv_text, "VIIRS_SNPP_NRT")[0]
        assert r["timestamp"].tzinfo == timezone.utc
        assert r["timestamp"].hour == 6
        assert r["timestamp"].minute == 30

    def test_error_response_returns_empty_list(self):
        records = parse_firms_csv('{"error": "invalid key"}', "VIIRS_SNPP_NRT")
        assert records == []

    def test_gas_flare_type(self):
        csv_text = f"{VIIRS_HEADER}\n{_viirs_row(fire_type='2')}"
        r = parse_firms_csv(csv_text, "VIIRS_SNPP_NRT")[0]
        assert r["type"] == "unknown"

    def test_industrial_fire_type(self):
        csv_text = f"{VIIRS_HEADER}\n{_viirs_row(fire_type='3')}"
        r = parse_firms_csv(csv_text, "VIIRS_SNPP_NRT")[0]
        assert r["type"] == "unknown"

    def test_frp_is_none_if_missing(self):
        csv_text = f"{VIIRS_HEADER}\n{_viirs_row(frp='')}"
        r = parse_firms_csv(csv_text, "VIIRS_SNPP_NRT")[0]
        assert r["frp"] is None


class TestParseMODISCsv:
    def test_parses_single_modis_row(self):
        csv_text = f"{MODIS_HEADER}\n{_modis_row()}"
        records = parse_firms_csv(csv_text, "MODIS_NRT")
        assert len(records) == 1
        r = records[0]
        assert r["confidence"] == 85.0
        assert r["type"] == "unknown"  # type=3 is always unknown
        assert r["frp"] == pytest.approx(5.2)

    def test_modis_confidence_capped_at_100(self):
        csv_text = f"{MODIS_HEADER}\n{_modis_row(confidence='105')}"
        r = parse_firms_csv(csv_text, "MODIS_NRT")[0]
        assert r["confidence"] == 100.0

    def test_modis_empty_csv(self):
        records = parse_firms_csv("", "MODIS_NRT")
        assert records == []
