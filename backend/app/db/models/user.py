"""
User model for ThermalTrace authentication.
"""
from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, String, DateTime
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: f"user-{uuid.uuid4().hex[:12]}")
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
