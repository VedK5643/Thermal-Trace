"""
Reports API endpoints for ThermalTrace.
Generates structured incident/intelligence reports in JSON, CSV, or text/PDF formats.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import io
import csv

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models.hotspot import Hotspot
from app.db.models.alert import Alert
from app.db.models.facility import Facility

router = APIRouter()


class ReportRequest(BaseModel):
    date_from: Optional[str] = Field(None, description="Start date ISO string")
    date_to: Optional[str] = Field(None, description="End date ISO string")
    state: Optional[str] = Field(None, description="Filter state")
    classification: Optional[str] = Field(None, description="Filter ML classification")
    severity: Optional[str] = Field(None, description="Filter severity")
    facility_id: Optional[str] = Field(None, description="Filter specific facility ID")
    format: str = Field("json", description="Output format: 'json', 'csv', or 'pdf'")


@router.post("/reports/generate")
async def generate_report(
    req: ReportRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a structured operational intelligence report for thermal observations, ML predictions, alerts, and facilities.
    """
    stmt = select(Hotspot)
    if req.state:
        stmt = stmt.where(Hotspot.state == req.state)
    if req.classification:
        stmt = stmt.where(Hotspot.ml_type == req.classification)
    if req.severity:
        stmt = stmt.where(Hotspot.severity == req.severity)

    stmt = stmt.limit(500)
    res = await db.execute(stmt)
    hotspots = res.scalars().all()

    total_obs = len(hotspots)
    class_counts = {"industrial_thermal_source": 0, "mining_thermal_source": 0, "natural_fire": 0, "unknown": 0}
    high_frp = 0
    persistent = 0

    incidents_list = []
    for h in hotspots:
        ml_t = getattr(h, "ml_type", "unknown") or "unknown"
        class_counts[ml_t] = class_counts.get(ml_t, 0) + 1
        if getattr(h, "frp", 0) and h.frp >= 35.0:
            high_frp += 1
        if getattr(h, "persistence_count", 0) >= 3:
            persistent += 1

        incidents_list.append({
            "id": h.id,
            "latitude": h.latitude,
            "longitude": h.longitude,
            "timestamp": h.timestamp.isoformat() if h.timestamp else None,
            "rawTelemetryType": getattr(h, "type", "unknown"),
            "rawConfidence": getattr(h, "confidence", 65.0),
            "predictedClassification": ml_t,
            "mlConfidence": getattr(h, "ml_confidence", 0.0),
            "frpMw": getattr(h, "frp", None),
            "severity": h.severity,
            "persistenceCount": getattr(h, "persistence_count", 0),
            "facilityDistanceKm": getattr(h, "facility_dist_km", None)
        })

    # Fetch alerts
    alert_stmt = select(Alert).limit(50)
    alert_res = await db.execute(alert_stmt)
    alerts = alert_res.scalars().all()
    alert_summary = {
        "critical": len([a for a in alerts if a.severity == "critical"]),
        "high": len([a for a in alerts if a.severity == "high"]),
        "medium": len([a for a in alerts if a.severity == "medium"]),
        "low": len([a for a in alerts if a.severity == "low"]),
        "total": len(alerts)
    }

    report_payload = {
        "reportMetadata": {
            "title": "ThermalTrace Operational Intelligence Report",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "scope": req.state or "India-Wide",
            "appliedFilters": {
                "dateFrom": req.date_from,
                "dateTo": req.date_to,
                "state": req.state,
                "classification": req.classification,
                "severity": req.severity,
                "facilityId": req.facility_id
            }
        },
        "executiveSummary": {
            "totalObservations": total_obs,
            "predictedIndustrialThermalSources": class_counts["industrial_thermal_source"],
            "predictedMiningThermalSources": class_counts["mining_thermal_source"],
            "predictedNaturalFires": class_counts["natural_fire"],
            "unknownObservations": class_counts["unknown"],
            "persistentThermalEvents": persistent,
            "highFrpEvents": high_frp,
            "totalActiveAlerts": alert_summary["total"]
        },
        "thermalActivityBreakdown": {
            "classificationDistribution": class_counts,
            "alertSeverityBreakdown": alert_summary
        },
        "scientificDisclosures": {
            "satelliteSource": "NASA FIRMS Satellite Thermal Anomaly Telemetry",
            "modelInformation": "ThermalTrace ML (model version thermalwatch-v1)",
            "benchmarkAccuracy": "Finalized 4-class taxonomy. OpenStreetMap industrial infrastructure provides corroborating geospatial evidence, not ground truth.",
            "nonCausationNotice": "Industrial facility proximity represents contextual spatial evidence, NOT proof of causation."
        },
        "incidentRecords": incidents_list[:50]
    }

    if req.format.lower() == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Incident ID", "Latitude", "Longitude", "Timestamp", "ML Prediction", "ML Confidence", "FRP (MW)", "Severity", "Facility Distance (km)"])
        for inc in incidents_list:
            writer.writerow([
                inc["id"],
                inc["latitude"],
                inc["longitude"],
                inc["timestamp"],
                inc["predictedClassification"],
                inc["mlConfidence"],
                inc["frpMw"],
                inc["severity"],
                inc["facilityDistanceKm"]
            ])
        return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=thermaltrace_report.csv"})

    return report_payload
