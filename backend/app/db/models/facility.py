"""
Facility database model.
Matches the frontend Facility TypeScript interface with additional
geographic fields for India-wide coverage.
"""
from sqlalchemy import Column, Float, Index, String
from geoalchemy2 import Geometry

from app.db.base import Base


class Facility(Base):
    """Industrial facility record."""

    __tablename__ = "facilities"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # refinery | power_plant | steel_plant | cement_plant | lng_terminal
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    city = Column(String, nullable=False)
    district = Column(String, nullable=True)
    state = Column(String, nullable=False)
    country = Column(String, nullable=False, default="India")
    source = Column(String, nullable=True, default="unknown")

    # PostGIS geometry column: POINT(longitude latitude), SRID 4326 (WGS84)
    geometry = Column(Geometry("POINT", srid=4326), nullable=True)

    __table_args__ = (
        Index("ix_facilities_type", "type"),
        Index("ix_facilities_state", "state"),
        Index("ix_facilities_city", "city"),
        Index("ix_facilities_geometry", "geometry", postgresql_using="gist"),
    )
