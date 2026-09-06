"""
API v1 router — aggregates all v1 route modules.
"""
from fastapi import APIRouter

from app.api.v1 import alerts, analytics, auth, chat, facilities, firms, health, hotspots, incidents, ingestion, reports

router = APIRouter(prefix="/api/v1")

router.include_router(health.router, tags=["Health"])
router.include_router(firms.router, tags=["FIRMS Status"])
router.include_router(auth.router, tags=["Authentication"])
router.include_router(hotspots.router, tags=["Hotspots"])
router.include_router(facilities.router, tags=["Facilities"])
router.include_router(alerts.router, tags=["Alerts"])
router.include_router(analytics.router, tags=["Analytics"])
router.include_router(reports.router, tags=["Reports"])
router.include_router(incidents.router, tags=["Incidents"])
router.include_router(ingestion.router, tags=["Ingestion"])
router.include_router(chat.router, tags=["Chat"])
