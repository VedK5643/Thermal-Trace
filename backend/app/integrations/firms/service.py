"""
FIRMS ingestion service.

Orchestrates the full ingest pipeline:
  FIRMSClient.fetch_csv()
      → parse_firms_csv() (normalizer)
      → deduplication check (DB id lookup)
      → bulk upsert into hotspots table

The upsert uses PostgreSQL's ON CONFLICT (id) DO NOTHING so the endpoint
is safe to call repeatedly — no duplicate rows are ever created.

Phase 5D: ingest_all_sources() fans out to all configured VIIRS NRT
satellites with per-source failure isolation. If one satellite source
fails, data from other sources is still persisted and the failure is
reported in the summary.
"""
import json
import logging
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.firms.client import FIRMSClient, INDIA_BBOX
from app.integrations.firms.normalizer import parse_firms_csv
from app.ml.inference import ml_inference_service

logger = logging.getLogger(__name__)

# Maximum records to process in a single ingestion run (per source).
# Raised from 1000 → 5000 to handle 5-day multi-source datasets.
_MAX_RECORDS_PER_SOURCE = 5000

# Records per SQL batch to avoid oversized parameter lists
_SQL_BATCH_SIZE = 500


class FIRMSIngestionService:
    """
    Fetches FIRMS data, normalizes it, and upserts into the hotspots table.
    """

    def __init__(self, db: AsyncSession, map_key: str):
        self._db = db
        self._client = FIRMSClient(map_key=map_key)

    # ------------------------------------------------------------------
    # Single-source ingestion (used by the single-source endpoint and
    # called internally by ingest_all_sources).
    # ------------------------------------------------------------------

    async def ingest(
        self,
        source: str = "VIIRS_SNPP_NRT",
        bbox: str = INDIA_BBOX,
        days: int = 1,
    ) -> Dict[str, Any]:
        """
        Run the full ingest pipeline for a single FIRMS source.

        Returns a summary dict:
          {
            "source":   str,
            "fetched":  int,   # rows in FIRMS response
            "inserted": int,   # new rows written to DB
            "skipped":  int,   # duplicates (already existed)
            "errors":   int,   # parse/fetch failures
          }
        """
        logger.info("FIRMS ingest started: source=%s bbox=%s days=%d", source, bbox, days)

        # 1. Fetch raw CSV from NASA FIRMS
        try:
            csv_text = await self._client.fetch_csv(source=source, bbox=bbox, days=days)
        except Exception as exc:
            logger.error("FIRMS fetch failed: %s", exc)
            raise

        # 2. Parse & normalize
        records = parse_firms_csv(csv_text, source)
        fetched = len(records)
        logger.info("FIRMS parse complete: %d records", fetched)

        if not records:
            return {
                "source": source,
                "fetched": 0,
                "inserted": 0,
                "skipped": 0,
                "errors": 0,
            }

        # 3. Deduplicate & upsert in batches (cap per source)
        capped = records[: _MAX_RECORDS_PER_SOURCE]
        inserted = 0
        skipped = 0

        for batch_start in range(0, len(capped), _SQL_BATCH_SIZE):
            batch = capped[batch_start: batch_start + _SQL_BATCH_SIZE]
            batch_inserted, batch_skipped = await self._upsert_batch(batch)
            inserted += batch_inserted
            skipped += batch_skipped

        logger.info(
            "FIRMS ingest complete: fetched=%d inserted=%d skipped=%d",
            fetched, inserted, skipped,
        )

        return {
            "source": source,
            "fetched": fetched,
            "inserted": inserted,
            "skipped": skipped,
            "errors": 0,
        }

    # ------------------------------------------------------------------
    # Multi-source ingestion — Phase 5D
    # ------------------------------------------------------------------

    async def ingest_all_sources(
        self,
        sources: List[str],
        bbox: str = INDIA_BBOX,
        days: int = 5,
    ) -> Dict[str, Any]:
        """
        Run the full ingest pipeline across all configured FIRMS sources.

        Each source is ingested independently. If one source raises an
        exception, the exception is caught, logged, and recorded in the
        `errors` list. Data from successful sources is always persisted.

        Args:
            sources: List of FIRMS source identifiers (e.g. ["VIIRS_SNPP_NRT", ...]).
            bbox:    Bounding box string "west,south,east,north" (default: India-wide).
            days:    Number of past days (1–10, capped by NASA API limit).

        Returns summary dict:
          {
            "sources_attempted": int,
            "sources_succeeded": int,
            "sources_failed":    int,
            "total_fetched":     int,
            "total_inserted":    int,
            "total_skipped":     int,
            "bbox":              str,
            "days":              int,
            "per_source":        [{"source": ..., "fetched": ..., "inserted": ..., "skipped": ..., "errors": ...}],
            "errors":            [{"source": ..., "error": str}],
          }
        """
        logger.info(
            "FIRMS multi-source ingest started: sources=%s bbox=%s days=%d",
            sources, bbox, days,
        )

        per_source_results: List[Dict[str, Any]] = []
        error_records: List[Dict[str, str]] = []

        for source in sources:
            try:
                result = await self.ingest(source=source, bbox=bbox, days=days)
                per_source_results.append(result)
                logger.info(
                    "Source %s: fetched=%d inserted=%d skipped=%d",
                    source, result["fetched"], result["inserted"], result["skipped"],
                )
            except Exception as exc:
                logger.error(
                    "FIRMS source %s failed (continuing with remaining sources): %s",
                    source, exc, exc_info=True,
                )
                error_records.append({"source": source, "error": str(exc)})
                try:
                    await self._db.rollback()
                except Exception:
                    pass
                # Do NOT re-raise — failure of one source must not block others

        total_fetched = sum(r["fetched"] for r in per_source_results)
        total_inserted = sum(r["inserted"] for r in per_source_results)
        total_skipped = sum(r["skipped"] for r in per_source_results)

        summary = {
            "sources_attempted": len(sources),
            "sources_succeeded": len(per_source_results),
            "sources_failed": len(error_records),
            "total_fetched": total_fetched,
            "total_inserted": total_inserted,
            "total_skipped": total_skipped,
            "bbox": bbox,
            "days": days,
            "per_source": per_source_results,
            "errors": error_records,
        }

        logger.info(
            "FIRMS multi-source ingest complete: attempted=%d succeeded=%d failed=%d "
            "total_fetched=%d total_inserted=%d total_skipped=%d",
            len(sources), len(per_source_results), len(error_records),
            total_fetched, total_inserted, total_skipped,
        )
        return summary

    # ------------------------------------------------------------------
    # Core DB operation
    # ------------------------------------------------------------------

    async def _upsert_batch(
        self, records: List[Dict[str, Any]]
    ) -> tuple[int, int]:
        """
        Upsert a batch of normalized records into the hotspots table.
        Uses ON CONFLICT (id) DO NOTHING for idempotent operation.
        Uses RETURNING id to count inserted rows accurately without a global
        COUNT(*) race condition.

        Returns (inserted_count, skipped_count).
        """
        if not records:
            return 0, 0

        # Upsert with source column for traceability and ML classification predictions.
        # RETURNING id gives us the exact set of rows that were inserted
        # (rows that matched ON CONFLICT are not returned).
        upsert_sql = text("""
            INSERT INTO hotspots (
                id, latitude, longitude, type, brightness, confidence,
                severity, timestamp, facility_id, status,
                country, state, city, district, source, geometry,
                ml_type, ml_confidence, model_version, ml_explanation, frp,
                land_cover_class, land_cover_name
            )
            VALUES (
                :id, :latitude, :longitude, :type, :brightness, :confidence,
                :severity, :timestamp, :facility_id, :status,
                :country, :state, :city, :district, :source,
                ST_SetSRID(ST_MakePoint(CAST(:geom_lon AS float8), CAST(:geom_lat AS float8)), 4326),
                :ml_type, :ml_confidence, :model_version, :ml_explanation, :frp,
                :land_cover_class, :land_cover_name
            )
            ON CONFLICT (id) DO NOTHING
            RETURNING id
        """)

        inserted = 0
        for record in records:
            params = {**record}
            params["geom_lon"] = record.get("longitude")
            params["geom_lat"] = record.get("latitude")
            params.setdefault("source", None)
            params["frp"] = record.get("frp")

            # Phase 6 — Execute ML inference with failure isolation
            try:
                pred = await ml_inference_service.predict_observation(
                    db=self._db,
                    latitude=record.get("latitude", 0.0),
                    longitude=record.get("longitude", 0.0),
                    timestamp=record.get("timestamp"),
                    frp=record.get("frp"),
                )
                params["ml_type"] = pred.ml_type
                params["ml_confidence"] = pred.ml_confidence
                params["model_version"] = pred.model_version
                params["ml_explanation"] = json.dumps(pred.ml_explanation) if pred.ml_explanation else None
            except Exception as ml_exc:
                logger.error("ML inference failed for observation %s (fallback to unknown): %s", record.get("id"), ml_exc)
                params["ml_type"] = "unknown"
                params["ml_confidence"] = 0.0
                params["model_version"] = "thermalwatch-v1"
                params["ml_explanation"] = json.dumps({"error": str(ml_exc)})

            # Land-cover enrichment (non-blocking: errors default to NULL)
            try:
                from app.services.landcover import get_land_cover
                lc_class, lc_name = get_land_cover(
                    lat=record.get("latitude", 0.0),
                    lon=record.get("longitude", 0.0),
                )
                params["land_cover_class"] = lc_class
                params["land_cover_name"] = lc_name
            except Exception as lc_exc:
                logger.debug("Land-cover lookup skipped for %s: %s", record.get("id"), lc_exc)
                params["land_cover_class"] = None
                params["land_cover_name"] = None

            result = await self._db.execute(upsert_sql, params)
            # RETURNING returns a row only when a row was actually inserted
            if result.fetchone() is not None:
                inserted += 1

                # Generate real-time alert for warning/critical or high ML confidence events
                sev = params.get("severity") or "info"
                if sev in ("warning", "critical") or params.get("ml_type") in ("industrial_thermal_source", "mining_thermal_source", "natural_fire"):
                    alert_id = f"ALT-{params['id']}"
                    title_label = (
                        "Predicted Industrial Source"
                        if params.get("ml_type") == "industrial_thermal_source"
                        else "High Thermal Anomaly Detected"
                    )
                    state_str = params.get("state") or "India"
                    msg = f"{title_label} at {state_str} ({params.get('latitude')}, {params.get('longitude')}) with confidence {params.get('confidence', 0)}%."

                    alert_sql = text("""
                        INSERT INTO alerts (id, hotspot_id, facility_id, severity, title, message, timestamp, acknowledged)
                        VALUES (:id, :hotspot_id, :facility_id, :severity, :title, :message, :timestamp, false)
                        ON CONFLICT (id) DO NOTHING;
                    """)
                    await self._db.execute(alert_sql, {
                        "id": alert_id,
                        "hotspot_id": params["id"],
                        "facility_id": params.get("facility_id"),
                        "severity": sev if sev in ("critical", "warning", "info") else "warning",
                        "title": title_label,
                        "message": msg,
                        "timestamp": params["timestamp"],
                    })

        await self._db.commit()

        skipped = len(records) - inserted
        return inserted, skipped
