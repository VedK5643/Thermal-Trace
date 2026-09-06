"""
FIRMS status API endpoints for ThermalTrace.
Provides lightweight status metadata without triggering external FIRMS requests.
"""
from fastapi import APIRouter
from app.services.firms_status import firms_sync_manager

router = APIRouter()


@router.get("/firms/status")
async def get_firms_status():
    """
    Get backend-owned FIRMS synchronization status metadata.
    Does NOT trigger external FIRMS API requests or return raw observation payloads.
    """
    return firms_sync_manager.get_status_payload()
