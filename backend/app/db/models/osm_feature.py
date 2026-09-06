"""
OSM Feature database model.
Dedicated table to hold ML-specific OpenStreetMap features (e.g., landuse, power plants)
to preserve parity with the original training notebook's proximity calculations.
"""
from datetime import datetime, timezone
from sqlalchemy import BigInteger, Column, DateTime, Float, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry

from app.db.base import Base

class OSMFeature(Base):
    """OpenStreetMap infrastructure feature for ML context."""

    __tablename__ = "osm_features"

    id = Column(String, primary_key=True)  # e.g., "node/123456"
    osm_type = Column(String, nullable=False)  # "node", "way", or "relation"
    osm_id = Column(BigInteger, nullable=False)
    feature_type = Column(String, nullable=False)  # e.g., "landuse_industrial", "power_plant"
    name = Column(String, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # PostGIS geometry column: POINT(longitude latitude), SRID 4326 (WGS84)
    geometry = Column(Geometry("POINT", srid=4326), nullable=True)

    raw_tags = Column(JSONB, nullable=True)
    imported_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_osm_features_type", "feature_type"),
        Index("ix_osm_features_geometry", "geometry", postgresql_using="gist"),
    )
