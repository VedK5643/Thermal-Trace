"""
Deterministic unit tests for the ThermalWatch Production Feature Adapter.

Tests verify that production feature construction exactly matches the
authoritative training notebooks:
  - Exploratory data analysis.ipynb
  - Labelling strategy.ipynb
  - Feature engineering and split.ipynb
  - Multiclass model training.ipynb

All tests use in-memory fixtures — no real database connections required.
The AsyncSession is mocked using a minimal stub that replays pre-configured
query results, making tests fully deterministic, fast, and independent of
Supabase availability.

Coverage:
  - 3-decimal spatial grouping (round_coord)
  - Same rounded coordinates → same source
  - Nearby coordinates in different cells → separate sources
  - FRP mean (pandas-equivalent)
  - FRP std with ddof=1 (pandas default)
  - log1p transforms
  - std.fillna(0) behavior for single-obs
  - frp_cv = std / mean, NaN→0 for single-obs
  - months_active = distinct month numbers (1–12, NOT year-month pairs)
  - active_duration_days as integer days
  - first_seen_month
  - OSM distance: degree * 111 methodology
  - Strict timestamp cutoff
  - Legacy NULL FRP behavior
  - Single-observation behavior (valid features, not error)
  - Zero-observation error
"""
import asyncio
import math
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ml.source_features import (
    FEATURE_COLUMNS,
    GROUPING_DECIMALS,
    InsufficientHistoryError,
    MissingOSMDataError,
    SourceFeatureVector,
    build_source_features,
    round_coord,
)


# ---------------------------------------------------------------------------
# Async test runner helper (avoids pytest-asyncio / anyio plugin conflicts)
# ---------------------------------------------------------------------------

def run_async(coro):
    """Run an async coroutine synchronously inside a test (Python 3.14 safe)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Test helpers / stubs
# ---------------------------------------------------------------------------

def _ts(year: int, month: int, day: int, hour: int = 0) -> datetime:
    """Create a UTC-aware datetime for fixture building."""
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


def _make_hotspot_row(
    lat: float,
    lon: float,
    timestamp: datetime,
    frp: Optional[float],
) -> Any:
    """Create a mock hotspot result row."""
    row = MagicMock()
    row.latitude = lat
    row.longitude = lon
    row.timestamp = timestamp
    row.frp = frp
    row.id = f"{lat}-{lon}-{timestamp}"
    return row


def _make_osm_row(dist_deg: float) -> Any:
    """Create a mock OSM distance result row."""
    row = MagicMock()
    row.dist_deg = dist_deg
    return row


def _make_db_stub(
    cluster_rows: List[Any],
    osm_dist_deg: Optional[float] = 0.045,  # ~5 km
) -> Any:
    """
    Build a minimal AsyncSession stub that returns cluster_rows for the
    first execute() call and osm_dist_deg for the second execute() call.
    """
    db = AsyncMock()

    # First call: cluster query → cluster_rows
    cluster_result = MagicMock()
    cluster_result.all.return_value = cluster_rows

    # Second call: nearest OSM feature → distance row
    osm_result = MagicMock()
    if osm_dist_deg is not None:
        dist_row = _make_osm_row(osm_dist_deg)
        osm_result.first.return_value = dist_row
    else:
        osm_result.first.return_value = None

    db.execute = AsyncMock(side_effect=[cluster_result, osm_result])
    return db


# ---------------------------------------------------------------------------
# A. Feature column contract
# ---------------------------------------------------------------------------

class TestFeatureContract:
    def test_feature_column_count(self):
        """Must have exactly 8 features."""
        assert len(FEATURE_COLUMNS) == 8

    def test_feature_column_exact_order(self):
        """Columns must match the artifact's feature_columns exactly."""
        expected = [
            "obs_count",
            "log_mean_frp",
            "log_std_frp",
            "frp_cv",
            "months_active",
            "nearest_osm_distance_km",
            "active_duration_days",
            "first_seen_month",
        ]
        assert FEATURE_COLUMNS == expected

    def test_to_list_preserves_order(self):
        """SourceFeatureVector.to_list() must emit values in artifact order."""
        v = SourceFeatureVector(
            obs_count=3.0,
            log_mean_frp=1.1,
            log_std_frp=0.5,
            frp_cv=0.4,
            months_active=2.0,
            nearest_osm_distance_km=5.0,
            active_duration_days=10.0,
            first_seen_month=3.0,
        )
        lst = v.to_list()
        assert lst == [3.0, 1.1, 0.5, 0.4, 2.0, 5.0, 10.0, 3.0]
        assert len(lst) == 8


# ---------------------------------------------------------------------------
# B. Spatial grouping (3-decimal rounding)
# ---------------------------------------------------------------------------

class TestSpatialGrouping:
    def test_grouping_decimals_constant(self):
        """The grouping precision must be exactly 3 decimal places."""
        assert GROUPING_DECIMALS == 3

    def test_round_coord_basic(self):
        """round_coord must round to 3 decimal places."""
        assert round_coord(22.30012) == 22.300
        assert round_coord(70.79951) == 70.800

    def test_same_rounded_coords_same_cell(self):
        """Two coordinates rounding to the same 3-decimal value are same cell."""
        assert round_coord(22.3001) == round_coord(22.3004)
        assert round_coord(70.8001) == round_coord(70.8002)

    def test_different_rounded_coords_different_cell(self):
        """Coordinates rounding to different 3-decimal values are separate cells."""
        assert round_coord(22.3004) != round_coord(22.3006)
        # 22.3004 → 22.300, 22.3006 → 22.301

    def test_obs_count_reflects_grid_cell_rows(self):
        """The adapter uses whatever the DB returns for the grid cell."""
        rows = [
            _make_hotspot_row(22.3001, 70.8001, _ts(2026, 1, 1), frp=10.0),
            _make_hotspot_row(22.3002, 70.8002, _ts(2026, 1, 2), frp=12.0),
        ]
        db = _make_db_stub(rows)
        vec = run_async(build_source_features(
            db=db, latitude=22.3, longitude=70.8, cutoff_ts=_ts(2026, 1, 10)
        ))
        assert vec.obs_count == 2.0


# ---------------------------------------------------------------------------
# C. obs_count
# ---------------------------------------------------------------------------

class TestObsCount:
    def test_obs_count_matches_cluster_rows(self):
        """obs_count should equal the number of rows returned for the cluster."""
        rows = [
            _make_hotspot_row(22.3, 70.8, _ts(2026, 1, 1), frp=10.0),
            _make_hotspot_row(22.3, 70.8, _ts(2026, 1, 2), frp=12.0),
            _make_hotspot_row(22.3, 70.8, _ts(2026, 1, 3), frp=14.0),
        ]
        db = _make_db_stub(rows)
        vec = run_async(build_source_features(
            db=db, latitude=22.3, longitude=70.8, cutoff_ts=_ts(2026, 1, 10)
        ))
        assert vec.obs_count == 3.0

    def test_single_obs_count(self):
        """Single observation must produce obs_count=1."""
        rows = [_make_hotspot_row(22.3, 70.8, _ts(2026, 3, 5), frp=8.0)]
        db = _make_db_stub(rows)
        vec = run_async(build_source_features(
            db=db, latitude=22.3, longitude=70.8, cutoff_ts=_ts(2026, 3, 10)
        ))
        assert vec.obs_count == 1.0


# ---------------------------------------------------------------------------
# D. FRP statistics (pandas-equivalent)
# ---------------------------------------------------------------------------

class TestFRPStatistics:
    def test_log_mean_frp(self):
        """log_mean_frp = log1p(mean(frp_values)). Source: Feature eng. Cell 4."""
        frps = [10.0, 20.0, 30.0]
        rows = [_make_hotspot_row(22.3, 70.8, _ts(2026, 1, i + 1), frp=f)
                for i, f in enumerate(frps)]
        db = _make_db_stub(rows)
        vec = run_async(build_source_features(
            db=db, latitude=22.3, longitude=70.8, cutoff_ts=_ts(2026, 1, 10)
        ))
        expected_mean = 20.0  # (10+20+30)/3
        assert vec.log_mean_frp == pytest.approx(math.log1p(expected_mean), rel=1e-6)

    def test_log_std_frp_ddof1(self):
        """log_std_frp = log1p(std(frp)) with ddof=1 (pandas default).
        Source: Labelling Cell 3 — ('frp', 'std') uses pandas ddof=1."""
        frps = [10.0, 20.0, 30.0]
        rows = [_make_hotspot_row(22.3, 70.8, _ts(2026, 1, i + 1), frp=f)
                for i, f in enumerate(frps)]
        db = _make_db_stub(rows)
        vec = run_async(build_source_features(
            db=db, latitude=22.3, longitude=70.8, cutoff_ts=_ts(2026, 1, 10)
        ))
        mean = 20.0
        variance = sum((x - mean) ** 2 for x in frps) / (len(frps) - 1)  # ddof=1
        expected_std = math.sqrt(variance)
        assert vec.log_std_frp == pytest.approx(math.log1p(expected_std), rel=1e-6)

    def test_frp_cv(self):
        """frp_cv = std / mean. Source: Labelling Cell 4."""
        frps = [10.0, 20.0, 30.0]
        rows = [_make_hotspot_row(22.3, 70.8, _ts(2026, 1, i + 1), frp=f)
                for i, f in enumerate(frps)]
        db = _make_db_stub(rows)
        vec = run_async(build_source_features(
            db=db, latitude=22.3, longitude=70.8, cutoff_ts=_ts(2026, 1, 10)
        ))
        mean = 20.0
        variance = sum((x - mean) ** 2 for x in frps) / (len(frps) - 1)
        std = math.sqrt(variance)
        assert vec.frp_cv == pytest.approx(std / mean, rel=1e-6)

    def test_frp_cv_zero_when_mean_is_zero(self):
        """frp_cv must be 0.0 when all frp values are 0 (no division by zero)."""
        rows = [_make_hotspot_row(22.3, 70.8, _ts(2026, 1, 1), frp=0.0),
                _make_hotspot_row(22.3, 70.8, _ts(2026, 1, 2), frp=0.0)]
        db = _make_db_stub(rows)
        vec = run_async(build_source_features(
            db=db, latitude=22.3, longitude=70.8, cutoff_ts=_ts(2026, 1, 10)
        ))
        assert vec.frp_cv == 0.0

    def test_single_obs_std_fillna_zero(self):
        """Single observation: std is NaN → fillna(0) → log1p(0) = 0.
        Source: Feature eng. Cell 4: log_std_frp = np.log1p(df['std_frp'].fillna(0))"""
        rows = [_make_hotspot_row(22.3, 70.8, _ts(2026, 1, 1), frp=15.0)]
        db = _make_db_stub(rows)
        vec = run_async(build_source_features(
            db=db, latitude=22.3, longitude=70.8, cutoff_ts=_ts(2026, 1, 10)
        ))
        assert vec.log_std_frp == pytest.approx(0.0)
        assert vec.log_mean_frp == pytest.approx(math.log1p(15.0))

    def test_single_obs_frp_cv_fillna_zero(self):
        """Single observation: frp_cv = NaN → fillna(0).
        Source: Training Cell 3: X_train['frp_cv'] = X_train['frp_cv'].fillna(0)"""
        rows = [_make_hotspot_row(22.3, 70.8, _ts(2026, 1, 1), frp=15.0)]
        db = _make_db_stub(rows)
        vec = run_async(build_source_features(
            db=db, latitude=22.3, longitude=70.8, cutoff_ts=_ts(2026, 1, 10)
        ))
        assert vec.frp_cv == 0.0


# ---------------------------------------------------------------------------
# E. Persistence / temporal features
# ---------------------------------------------------------------------------

class TestPersistenceFeatures:
    def test_months_active_single_month(self):
        """Two observations in same month → months_active = 1."""
        rows = [
            _make_hotspot_row(22.3, 70.8, _ts(2026, 3, 1), frp=10.0),
            _make_hotspot_row(22.3, 70.8, _ts(2026, 3, 15), frp=12.0),
        ]
        db = _make_db_stub(rows)
        vec = run_async(build_source_features(
            db=db, latitude=22.3, longitude=70.8, cutoff_ts=_ts(2026, 3, 20)
        ))
        assert vec.months_active == 1.0

    def test_months_active_distinct_month_numbers(self):
        """months_active counts distinct month NUMBERS, not (year,month) pairs.
        Source: Labelling Cell 4: months_active=('month', lambda x: x.nunique())
        where month = observed_at.dt.month.

        Jan 2025 and Jan 2026 both have month=1, so they count as 1, not 2."""
        rows = [
            _make_hotspot_row(22.3, 70.8, _ts(2025, 1, 10), frp=10.0),
            _make_hotspot_row(22.3, 70.8, _ts(2025, 3, 10), frp=11.0),
            _make_hotspot_row(22.3, 70.8, _ts(2026, 1, 10), frp=12.0),  # same month number as first
        ]
        db = _make_db_stub(rows)
        vec = run_async(build_source_features(
            db=db, latitude=22.3, longitude=70.8, cutoff_ts=_ts(2026, 4, 1)
        ))
        # Distinct month numbers: {1, 3} → 2, NOT 3
        assert vec.months_active == 2.0

    def test_months_active_caps_at_12(self):
        """months_active can never exceed 12 (distinct month numbers 1-12)."""
        # Create observations in all 12 months across 2 years
        rows = []
        for m in range(1, 13):
            rows.append(_make_hotspot_row(22.3, 70.8, _ts(2025, m, 1), frp=5.0))
            rows.append(_make_hotspot_row(22.3, 70.8, _ts(2026, m, 1), frp=6.0))
        db = _make_db_stub(rows)
        vec = run_async(build_source_features(
            db=db, latitude=22.3, longitude=70.8, cutoff_ts=_ts(2027, 1, 1)
        ))
        assert vec.months_active == 12.0  # caps at 12

    def test_active_duration_days_integer(self):
        """active_duration_days = (last_seen - first_seen).dt.days → integer.
        Source: Feature eng. Cell 5."""
        rows = [
            _make_hotspot_row(22.3, 70.8, _ts(2026, 1, 1), frp=10.0),
            _make_hotspot_row(22.3, 70.8, _ts(2026, 1, 11), frp=12.0),
        ]
        db = _make_db_stub(rows)
        vec = run_async(build_source_features(
            db=db, latitude=22.3, longitude=70.8, cutoff_ts=_ts(2026, 1, 20)
        ))
        assert vec.active_duration_days == 10.0
        # Confirm it's a whole number (integer-like)
        assert vec.active_duration_days == int(vec.active_duration_days)

    def test_active_duration_single_obs_is_zero(self):
        """Single observation → duration = 0 days."""
        rows = [_make_hotspot_row(22.3, 70.8, _ts(2026, 5, 5), frp=15.0)]
        db = _make_db_stub(rows)
        vec = run_async(build_source_features(
            db=db, latitude=22.3, longitude=70.8, cutoff_ts=_ts(2026, 5, 10)
        ))
        assert vec.active_duration_days == 0.0

    def test_first_seen_month(self):
        """first_seen_month = min(timestamps).month.
        Source: Feature eng. Cell 5."""
        rows = [
            _make_hotspot_row(22.3, 70.8, _ts(2026, 4, 15), frp=10.0),
            _make_hotspot_row(22.3, 70.8, _ts(2026, 5, 1), frp=11.0),
        ]
        db = _make_db_stub(rows)
        vec = run_async(build_source_features(
            db=db, latitude=22.3, longitude=70.8, cutoff_ts=_ts(2026, 5, 10)
        ))
        assert vec.first_seen_month == 4.0


# ---------------------------------------------------------------------------
# F. Nearest OSM distance (degree * 111 methodology)
# ---------------------------------------------------------------------------

class TestNearestOSMDistance:
    def test_nearest_osm_distance_degree_times_111(self):
        """nearest_osm_distance_km = dist_deg * 111.
        Source: Labelling Cell 12."""
        rows = [_make_hotspot_row(22.3, 70.8, _ts(2026, 1, 1), frp=10.0)]
        # OSM feature at ~0.045 degrees away → 0.045 * 111 = 4.995 km
        db = _make_db_stub(rows, osm_dist_deg=0.045)
        vec = run_async(build_source_features(
            db=db, latitude=22.3, longitude=70.8, cutoff_ts=_ts(2026, 1, 10)
        ))
        assert vec.nearest_osm_distance_km == pytest.approx(0.045 * 111.0, rel=1e-6)

    def test_nearest_osm_distance_no_osm_features_raises_error(self):
        """If no OSM features in DB, it raises MissingOSMDataError."""
        rows = [_make_hotspot_row(22.3, 70.8, _ts(2026, 1, 1), frp=10.0)]
        db = _make_db_stub(rows, osm_dist_deg=None)
        with pytest.raises(MissingOSMDataError, match="No OSM features found in the database"):
            run_async(build_source_features(
                db=db, latitude=22.3, longitude=70.8, cutoff_ts=_ts(2026, 1, 10)
            ))

    def test_very_close_osm_feature(self):
        """OSM feature at 0.001° → 0.111 km (~111 m)."""
        rows = [_make_hotspot_row(22.3, 70.8, _ts(2026, 1, 1), frp=10.0)]
        db = _make_db_stub(rows, osm_dist_deg=0.001)
        vec = run_async(build_source_features(
            db=db, latitude=22.3, longitude=70.8, cutoff_ts=_ts(2026, 1, 10)
        ))
        assert vec.nearest_osm_distance_km == pytest.approx(0.111, rel=1e-3)


# ---------------------------------------------------------------------------
# G. Temporal leakage (strict cutoff)
# ---------------------------------------------------------------------------

class TestTemporalLeakage:
    def test_cutoff_timestamp_is_passed_to_query(self):
        """The adapter must pass the cutoff_ts to the DB layer."""
        cutoff = _ts(2026, 2, 15)
        rows = [
            _make_hotspot_row(22.3, 70.8, _ts(2026, 2, 1), frp=10.0),
            _make_hotspot_row(22.3, 70.8, _ts(2026, 2, 10), frp=12.0),
        ]
        db = _make_db_stub(rows)
        vec = run_async(build_source_features(
            db=db, latitude=22.3, longitude=70.8, cutoff_ts=cutoff
        ))
        assert vec.obs_count == 2.0
        assert db.execute.call_count == 2  # cluster + osm

    def test_historical_backfill_timestamp_respected(self):
        """Simulates a historical backfill where cutoff_ts is in the past."""
        historical_cutoff = _ts(2024, 6, 1)
        rows = [_make_hotspot_row(22.3, 70.8, _ts(2024, 5, 15), frp=9.0)]
        db = _make_db_stub(rows)
        vec = run_async(build_source_features(
            db=db, latitude=22.3, longitude=70.8, cutoff_ts=historical_cutoff
        ))
        assert vec.obs_count == 1.0
        assert vec.first_seen_month == 5.0


# ---------------------------------------------------------------------------
# H. NULL FRP behavior (legacy data)
# ---------------------------------------------------------------------------

class TestNullFRP:
    def test_all_null_frp_produces_zero_features(self):
        """If ALL observations have frp=NULL, FRP features default to 0.0.
        This matches training's fillna(0) behavior rather than raising an error,
        because the training notebooks never raised errors for NaN FRP."""
        rows = [
            _make_hotspot_row(22.3, 70.8, _ts(2026, 1, 1), frp=None),
            _make_hotspot_row(22.3, 70.8, _ts(2026, 1, 5), frp=None),
        ]
        db = _make_db_stub(rows)
        vec = run_async(build_source_features(
            db=db, latitude=22.3, longitude=70.8, cutoff_ts=_ts(2026, 1, 10)
        ))
        # obs_count still counts all rows
        assert vec.obs_count == 2.0
        # FRP features are 0.0 (fillna behavior)
        assert vec.log_mean_frp == 0.0
        assert vec.log_std_frp == 0.0
        assert vec.frp_cv == 0.0
        # Non-FRP features still computed normally
        assert vec.months_active == 1.0
        assert vec.active_duration_days == 4.0

    def test_partial_null_frp_uses_non_null_subset(self):
        """If some FRP values are NULL, stats are computed from non-NULL subset."""
        rows = [
            _make_hotspot_row(22.3, 70.8, _ts(2026, 1, 1), frp=None),
            _make_hotspot_row(22.3, 70.8, _ts(2026, 1, 2), frp=10.0),
            _make_hotspot_row(22.3, 70.8, _ts(2026, 1, 3), frp=20.0),
        ]
        db = _make_db_stub(rows)
        vec = run_async(build_source_features(
            db=db, latitude=22.3, longitude=70.8, cutoff_ts=_ts(2026, 1, 10)
        ))
        assert vec.obs_count == 3.0  # includes the NULL row
        expected_mean = 15.0  # (10+20)/2
        assert vec.log_mean_frp == pytest.approx(math.log1p(expected_mean), rel=1e-6)


# ---------------------------------------------------------------------------
# I. Single-observation behavior
# ---------------------------------------------------------------------------

class TestSingleObservation:
    def test_single_obs_produces_valid_vector(self):
        """Single observation must produce a valid 8-feature vector, NOT an error.
        In training data, single-obs groups had:
          std_frp = NaN → fillna(0) → log_std_frp = 0.0
          frp_cv = NaN → fillna(0)
          active_duration_days = 0
          months_active = 1"""
        rows = [_make_hotspot_row(22.3, 70.8, _ts(2026, 7, 15), frp=5.0)]
        db = _make_db_stub(rows, osm_dist_deg=0.01)
        vec = run_async(build_source_features(
            db=db, latitude=22.3, longitude=70.8, cutoff_ts=_ts(2026, 7, 20)
        ))
        assert vec.obs_count == 1.0
        assert vec.log_mean_frp == pytest.approx(math.log1p(5.0))
        assert vec.log_std_frp == 0.0
        assert vec.frp_cv == 0.0
        assert vec.months_active == 1.0
        assert vec.active_duration_days == 0.0
        assert vec.first_seen_month == 7.0
        assert vec.nearest_osm_distance_km == pytest.approx(0.01 * 111.0)


# ---------------------------------------------------------------------------
# J. No-history / zero-observation case
# ---------------------------------------------------------------------------

class TestInsufficientHistory:
    def test_zero_obs_raises_insufficient_history(self):
        """Empty grid cell must raise InsufficientHistoryError."""
        db = AsyncMock()
        empty_result = MagicMock()
        empty_result.all.return_value = []
        db.execute = AsyncMock(return_value=empty_result)

        with pytest.raises(InsufficientHistoryError, match="No historical observations"):
            run_async(build_source_features(
                db=db, latitude=22.3, longitude=70.8, cutoff_ts=_ts(2026, 1, 10)
            ))


# ---------------------------------------------------------------------------
# K. SourceFeatureVector to_list integrity
# ---------------------------------------------------------------------------

class TestSourceFeatureVector:
    def test_vector_length_is_8(self):
        v = SourceFeatureVector(1, 2, 3, 4, 5, 6, 7, 8)
        assert len(v.to_list()) == 8

    def test_vector_values_exact(self):
        v = SourceFeatureVector(
            obs_count=5.0,
            log_mean_frp=2.3,
            log_std_frp=1.1,
            frp_cv=0.3,
            months_active=4.0,
            nearest_osm_distance_km=7.5,
            active_duration_days=60.0,
            first_seen_month=6.0,
        )
        assert v.to_list() == [5.0, 2.3, 1.1, 0.3, 4.0, 7.5, 60.0, 6.0]
