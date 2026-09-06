"""
ThermalWatch Production Feature Adapter.

Constructs the 8 source-level cluster features required by thermalwatch_model.joblib
from historical observations stored in the Supabase PostGIS hotspots table.

Feature contract (exact order matches artifact's feature_columns):
  0: obs_count               — total observations in the spatial grid cell up to T
  1: log_mean_frp            — log1p(mean(frp)) for cell obs with non-NULL frp
  2: log_std_frp             — log1p(std(frp).fillna(0)); ddof=1, NaN→0 for single obs
  3: frp_cv                  — std_frp / mean_frp; NaN→0 for single obs
  4: months_active           — count of distinct calendar month NUMBERS (1–12), caps at 12
  5: nearest_osm_distance_km — Euclidean degree distance * 111 to nearest facility
  6: active_duration_days    — (max_timestamp - min_timestamp).days as integer
  7: first_seen_month        — calendar month (1–12) of the earliest observation

Spatial grouping methodology (recovered from authoritative notebooks):
  The training dataset grouped 5,706,071 raw FIRMS observations into 4,714,657
  spatial source groups using:

    group_id = round(latitude, 3).str + '_' + round(longitude, 3).str

  This creates a deterministic grid where each cell spans ≈0.001° (≈111 m).
  In production we reproduce this by querying all hotspots whose
  round(latitude, 3) and round(longitude, 3) match the incoming observation's
  rounded coordinates.

  Source: Labelling strategy.ipynb Cell 2

OSM distance methodology:
  The training notebooks used scipy.spatial.cKDTree on raw (lat, lon) degree
  coordinates, producing Euclidean distance in degrees, then multiplied by 111
  to approximate km. This does NOT use geodesic distance or cos(lat) correction.

  In production, the facilities table may not be the exact same population as
  the 80,687-element OSM Overpass export used in training. This is a KNOWN
  discrepancy documented in the Phase 7G report.

  Where possible, production uses the same degree * 111 approximation to match
  training semantics. If PostGIS ST_Distance is used instead (geodesic), the
  systematic difference is documented.

  Source: Labelling strategy.ipynb Cell 11–12

Temporal leakage:
  ALL database queries are bounded by `timestamp <= cutoff_ts` where
  cutoff_ts is the timestamp of the incoming observation. This ensures that
  features for an observation at time T never incorporate any observation
  after T. This is a deliberate production constraint NOT present in the
  training notebooks (which used all historical data).

NULL FRP handling:
  The training data had zero FRP nulls. In production, legacy hotspots
  ingested before Phase 7C may have frp=NULL. These observations still
  contribute to obs_count, months_active, active_duration_days, and
  first_seen_month. FRP statistics (log_mean_frp, log_std_frp, frp_cv) are
  computed from the non-NULL subset only. If ALL observations have NULL FRP,
  FRP features default to 0.0 (matching the training's fillna(0) behavior
  for single-obs groups that also produced NaN std/cv).
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from sqlalchemy import cast, func, select, text, Numeric
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.osm_feature import OSMFeature
from app.db.models.hotspot import Hotspot

logger = logging.getLogger(__name__)

# The exact feature column order that the artifact expects.
FEATURE_COLUMNS: List[str] = [
    "obs_count",
    "log_mean_frp",
    "log_std_frp",
    "frp_cv",
    "months_active",
    "nearest_osm_distance_km",
    "active_duration_days",
    "first_seen_month",
]

# Spatial grouping precision: 3 decimal places on lat/lon.
# Derived from: Labelling strategy.ipynb Cell 2
#   df['group_id'] = df['latitude'].round(3).astype(str) + '_' + df['longitude'].round(3).astype(str)
GROUPING_DECIMALS: int = 3


def round_coord(value: float) -> float:
    """Round a coordinate to GROUPING_DECIMALS places, matching pandas round(3)."""
    return round(value, GROUPING_DECIMALS)


@dataclass
class SourceFeatureVector:
    """
    The 8 source-level features in artifact order.
    All values are floats, suitable for direct model input.
    """
    obs_count: float
    log_mean_frp: float
    log_std_frp: float
    frp_cv: float
    months_active: float
    nearest_osm_distance_km: float
    active_duration_days: float
    first_seen_month: float

    def to_list(self) -> List[float]:
        """Return features in the exact artifact order."""
        return [
            self.obs_count,
            self.log_mean_frp,
            self.log_std_frp,
            self.frp_cv,
            self.months_active,
            self.nearest_osm_distance_km,
            self.active_duration_days,
            self.first_seen_month,
        ]


class InsufficientHistoryError(Exception):
    """
    Raised when the spatial grid cell has zero historical observations,
    making feature computation impossible without fabricating data.

    Callers must catch this and decide on a fallback strategy
    (e.g., skip ML classification for this observation).
    """
    pass


class MissingOSMDataError(Exception):
    """
    Raised when the osm_features table is empty.
    The ML model cannot reliably predict without this context.
    """
    pass


async def build_source_features(
    *,
    db: AsyncSession,
    latitude: float,
    longitude: float,
    cutoff_ts: datetime,
    current_frp: Optional[float] = None,
    allow_single_obs_fallback: bool = False,
) -> SourceFeatureVector:
    """
    Build the 8 source-level features for the grid cell containing
    (latitude, longitude), using only observations with timestamp <= cutoff_ts.

    Spatial grouping reproduces the training notebook's:
        group_id = round(latitude, 3) + '_' + round(longitude, 3)

    Args:
        db:                         Open async SQLAlchemy session.
        latitude:                   Latitude of the incoming observation.
        longitude:                  Longitude of the incoming observation.
        cutoff_ts:                  Strict temporal cutoff. No observation after this timestamp
                                    may contribute to any feature.
        current_frp:                Optional FRP of the incoming observation if not yet in DB.
        allow_single_obs_fallback:  If True and DB has 0 prior rows, treats the incoming
                                    observation as a single-observation cluster (obs_count=1).

    Returns:
        SourceFeatureVector with all 8 features computed.

    Raises:
        InsufficientHistoryError: if the grid cell has zero observations
                                  before cutoff_ts and fallback is disabled.
    """
    # -------------------------------------------------------------------
    # 1. Compute the grid cell key (round to 3 decimal places).
    #    This matches: df['latitude'].round(3) in the training notebooks.
    # -------------------------------------------------------------------
    rounded_lat = round_coord(latitude)
    rounded_lon = round_coord(longitude)

    # -------------------------------------------------------------------
    # 2. Query all observations in this grid cell (timestamp <= cutoff_ts).
    #    Uses PostgreSQL ROUND() to match pandas rounding behavior.
    # -------------------------------------------------------------------
    cluster_query = (
        select(
            Hotspot.id,
            Hotspot.latitude,
            Hotspot.longitude,
            Hotspot.timestamp,
            Hotspot.frp,
        )
        .where(
            func.round(cast(Hotspot.latitude, Numeric), GROUPING_DECIMALS) == rounded_lat
        )
        .where(
            func.round(cast(Hotspot.longitude, Numeric), GROUPING_DECIMALS) == rounded_lon
        )
        .where(Hotspot.timestamp <= cutoff_ts)
    )

    result = await db.execute(cluster_query)
    rows = result.all()

    obs_count = len(rows)
    if obs_count == 0:
        if allow_single_obs_fallback:
            timestamps = [cutoff_ts]
            frp_values = [current_frp] if current_frp is not None else []
            obs_count = 1
        else:
            raise InsufficientHistoryError(
                f"No historical observations found for grid cell "
                f"({rounded_lat}, {rounded_lon}) before {cutoff_ts}. "
                f"Cannot compute features without fabricating values."
            )
    else:
        timestamps = [r.timestamp for r in rows]
        frp_values = [r.frp for r in rows if r.frp is not None]
        if current_frp is not None and not any(r.timestamp == cutoff_ts and r.frp == current_frp for r in rows):
            frp_values.append(current_frp)
            timestamps.append(cutoff_ts)
            obs_count = len(timestamps)

    # -------------------------------------------------------------------
    # 3. Extract timestamp and FRP series statistics.
    # -------------------------------------------------------------------


    min_ts = min(timestamps)
    max_ts = max(timestamps)

    # -------------------------------------------------------------------
    # 4. Temporal / persistence features.
    #    Source: Feature engineering and split.ipynb Cell 5
    #      active_duration_days = (last_seen - first_seen).dt.days  → integer
    #      first_seen_month = first_seen.dt.month
    #    Source: Labelling strategy.ipynb Cell 4
    #      months_active = ('month', lambda x: x.nunique())
    #      where month = observed_at.dt.month  → distinct month NUMBERS 1-12
    # -------------------------------------------------------------------
    active_duration_days = float((max_ts - min_ts).days)  # integer days like .dt.days
    first_seen_month = float(min_ts.month)
    # Distinct calendar month numbers (1-12), NOT (year, month) pairs.
    months_active = float(len({t.month for t in timestamps}))

    # -------------------------------------------------------------------
    # 5. FRP statistics.
    #    Source: Labelling strategy.ipynb Cell 3
    #      mean_frp = ('frp', 'mean')
    #      std_frp = ('frp', 'std')          → pandas default ddof=1
    #    Source: Feature engineering and split.ipynb Cell 4
    #      log_mean_frp = np.log1p(mean_frp)
    #      log_std_frp = np.log1p(std_frp.fillna(0))
    #    Source: Labelling strategy.ipynb Cell 4
    #      frp_cv = std_frp / mean_frp
    #    Source: Multiclass model training.ipynb Cell 3
    #      X_train['frp_cv'] = X_train['frp_cv'].fillna(0)
    #
    #    NULL FRP handling in production:
    #      Training data had zero FRP nulls. In production, legacy hotspots
    #      may have frp=NULL. We compute FRP stats from non-NULL subset.
    #      If ALL obs have NULL FRP, we treat it like a zero-FRP scenario
    #      (all FRP features = 0.0) rather than raising an error, because
    #      the training notebooks never raised errors for edge cases.
    # -------------------------------------------------------------------
    if len(frp_values) == 0:
        # All observations have NULL FRP (legacy pre-Phase7C data).
        # Default all FRP features to 0.0, matching the training's
        # fillna(0) behavior for degenerate cases.
        logger.warning(
            "Grid cell (%s, %s) has %d observations but ALL have frp=NULL. "
            "Setting FRP features to 0.0 (fillna behavior).",
            rounded_lat, rounded_lon, obs_count,
        )
        log_mean_frp = 0.0
        log_std_frp = 0.0
        frp_cv = 0.0
    elif len(frp_values) == 1:
        # Single FRP value: mean is defined, std is NaN (pandas behavior).
        # log_std_frp = log1p(NaN.fillna(0)) = log1p(0) = 0.0
        # frp_cv = NaN / mean = NaN → fillna(0) = 0.0
        frp_mean = frp_values[0]
        log_mean_frp = math.log1p(frp_mean)
        log_std_frp = 0.0   # log1p(fillna(0))
        frp_cv = 0.0        # fillna(0)
    else:
        # Multiple FRP values: compute mean and sample std (ddof=1).
        frp_mean = sum(frp_values) / len(frp_values)
        variance = sum((x - frp_mean) ** 2 for x in frp_values) / (len(frp_values) - 1)
        frp_std = math.sqrt(variance)

        log_mean_frp = math.log1p(frp_mean)
        log_std_frp = math.log1p(frp_std)

        # frp_cv = std / mean. If mean is 0 (all FRP = 0), this is NaN-like → 0.
        if frp_mean > 0:
            frp_cv = frp_std / frp_mean
        else:
            frp_cv = 0.0

    # -------------------------------------------------------------------
    # 6. Nearest OSM distance.
    #    Source: Labelling strategy.ipynb Cell 11-12
    #      cKDTree Euclidean distance in degree space, then * 111.
    #
    #    Production matches this exact logic by querying the dedicated
    #    osm_features table which mirrors the Overpass API extraction.
    # -------------------------------------------------------------------
    nearest_osm_distance_km: float = await _nearest_osm_distance_km_degree(
        db=db, latitude=rounded_lat, longitude=rounded_lon
    )

    return SourceFeatureVector(
        obs_count=float(obs_count),
        log_mean_frp=log_mean_frp,
        log_std_frp=log_std_frp,
        frp_cv=frp_cv,
        months_active=months_active,
        nearest_osm_distance_km=nearest_osm_distance_km,
        active_duration_days=active_duration_days,
        first_seen_month=first_seen_month,
    )


async def _nearest_osm_distance_km_degree(
    db: AsyncSession,
    latitude: float,
    longitude: float,
) -> float:
    """
    Returns the nearest OSM feature distance in km using the same methodology
    as the training notebooks: Euclidean distance in degree space * 111.

    Source: Labelling strategy.ipynb Cell 11-12
      distances, indices = tree.query(group_coords, k=1)  # cKDTree, degree space
      nearest_osm_distance_km = nearest_osm_distance_deg * 111

    Raises MissingOSMDataError if no features exist in the database.
    """
    # Compute Euclidean distance in degree space using SQL:
    #   sqrt((lat1 - lat2)^2 + (lon1 - lon2)^2)
    # Then multiply by 111 to convert to approximate km.
    # This matches cKDTree's Euclidean distance on (lat, lon) pairs.
    dist_deg_expr = func.sqrt(
        func.power(OSMFeature.latitude - latitude, 2)
        + func.power(OSMFeature.longitude - longitude, 2)
    )

    dist_query = (
        select(dist_deg_expr.label("dist_deg"))
        .order_by(dist_deg_expr)
        .limit(1)
    )

    result = await db.execute(dist_query)
    row = result.first()

    if row is None:
        raise MissingOSMDataError("No OSM features found in the database. Run ingest_osm_features.py.")

    return float(row.dist_deg) * 111.0
