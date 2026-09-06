"""
ThermalTrace FastAPI application entry point.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.exceptions import (
    DatabaseError,
    NotFoundError,
    database_error_handler,
    not_found_handler,
)

from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup/shutdown logging, DB init, and FIRMS sync scheduling."""
    logger.info("ThermalTrace API starting up...")
    logger.info("Environment: %s", settings.environment)
    logger.info("Frontend origin: %s", settings.frontend_origin)
    logger.info("API docs available at /docs")
    try:
        from app.db.session import init_db
        await init_db()
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.warning("DB table creation notice: %s", e)

    # Initialize FIRMS sync manager from existing database & start 6-hour background scheduler
    try:
        from app.services.firms_status import firms_sync_manager
        await firms_sync_manager.initialize_from_db()
        firms_sync_manager.start_scheduler_task()
        logger.info("FIRMS Sync Manager initialized. Status: %s. 6-hour scheduler active.", firms_sync_manager.get_status_classification())
    except Exception as e:
        logger.warning("FIRMS Sync Manager initialization notice: %s", e)

    yield
    logger.info("ThermalTrace API shutting down...")
    try:
        from app.services.firms_status import firms_sync_manager
        firms_sync_manager.stop_scheduler_task()
    except Exception:
        pass


# Create FastAPI application
app = FastAPI(
    title="ThermalTrace API",
    description="Geospatial thermal intelligence platform API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware — restricted to configured frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(NotFoundError, not_found_handler)  # type: ignore[arg-type]
app.add_exception_handler(DatabaseError, database_error_handler)  # type: ignore[arg-type]

# Include API v1 router
app.include_router(v1_router)

