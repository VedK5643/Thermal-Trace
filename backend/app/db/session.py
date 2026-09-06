"""
Database session management.
Provides async SQLAlchemy engine and session factory for FastAPI dependency injection.
"""
import logging
from collections.abc import AsyncGenerator

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create async engine using configured URL
engine_kwargs = {
    "echo": False,
    "connect_args": {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }
}
import sys

if settings.testing or "pytest" in sys.modules:
    engine_kwargs["poolclass"] = pool.NullPool
else:
    # pool_pre_ping is intentionally disabled: Supabase uses PgBouncer in
    # transaction-pool mode, which doesn't support the prepared statement used
    # by pool_pre_ping. The statement_cache_size=0 connect_arg handles the
    # DuplicatePreparedStatementError for our own queries.
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10
    engine_kwargs["pool_recycle"] = 300
    engine_kwargs["pool_timeout"] = 15


engine = create_async_engine(settings.get_database_url, **engine_kwargs)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency provider yielding async SQLAlchemy session."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Ensure database tables exist on startup."""
    from app.db.base import Base
    from app.db.models import User, Hotspot, Facility, Alert  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
