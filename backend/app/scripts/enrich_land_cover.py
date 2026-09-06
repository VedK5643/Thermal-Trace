"""
Batch land-cover enrichment script.

Backfills ESA WorldCover 10m land-cover classification for all hotspots
that currently have NULL land_cover_class.

Uses tile-grouped batch sampling for efficiency (~30-60 seconds for 80K+ points).

Usage:
    cd backend
    python -m app.scripts.enrich_land_cover
"""
import asyncio
import logging
import sys
from collections import defaultdict
from typing import Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.services.landcover import (
    _get_tile_id,
    ESA_WORLDCOVER_CLASSES,
    _ESA_COG_URL_TEMPLATE,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


async def enrich_land_cover():
    """Batch-enrich all hotspots missing land_cover_class."""

    try:
        import rasterio
    except ImportError:
        logger.error("rasterio is not installed. Run: pip install rasterio>=1.3.0")
        sys.exit(1)

    db_url = settings.database_url_direct or settings.database_url
    engine = create_async_engine(db_url, poolclass=NullPool)

    async with engine.begin() as conn:
        # Fetch all hotspots needing enrichment
        result = await conn.execute(
            text("SELECT id, latitude, longitude FROM hotspots WHERE land_cover_class IS NULL")
        )
        rows = result.fetchall()

    if not rows:
        logger.info("✅ No hotspots need land-cover enrichment.")
        return

    logger.info(f"🌍 Enriching {len(rows)} hotspots with ESA WorldCover 10m land-cover...")

    # Group by ESA 3×3° tile
    tile_groups: dict[str, list[Tuple[int, str, float, float]]] = defaultdict(list)
    for row in rows:
        hs_id, lat, lon = row[0], float(row[1]), float(row[2])
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            tile_id = _get_tile_id(lat, lon)
            tile_groups[tile_id].append((0, hs_id, lon, lat))

    logger.info(f"📦 Grouped into {len(tile_groups)} ESA WorldCover tiles")

    updates: list[Tuple[int, str, str]] = []

    env_opts = {
        "AWS_NO_SIGN_REQUEST": "YES",
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
        "GDAL_HTTP_TIMEOUT": "15",
        "GDAL_HTTP_MAX_RETRY": "2",
    }

    with rasterio.Env(**env_opts):
        for i, (tile_id, points) in enumerate(tile_groups.items()):
            url = _ESA_COG_URL_TEMPLATE.format(tile_id=tile_id)
            coords = [(lon, lat) for _, _, lon, lat in points]

            try:
                with rasterio.open(url) as src:
                    sampled = list(src.sample(coords))

                for (_, hs_id, _, _), val in zip(points, sampled):
                    class_id = int(val[0]) if val is not None and len(val) > 0 else 0
                    if class_id and class_id != 0:
                        class_name = ESA_WORLDCOVER_CLASSES.get(class_id, "Unknown")
                        updates.append((class_id, class_name, hs_id))

                logger.info(
                    f"  Tile {i+1}/{len(tile_groups)} ({tile_id}): "
                    f"sampled {len(points)} points"
                )
            except Exception as e:
                logger.warning(f"  ⚠ Tile {tile_id} failed: {e}")

    # Bulk update database
    if updates:
        async with engine.begin() as conn:
            update_sql = text(
                "UPDATE hotspots SET land_cover_class = :lc_class, "
                "land_cover_name = :lc_name WHERE id = :hs_id"
            )
            for lc_class, lc_name, hs_id in updates:
                await conn.execute(
                    update_sql,
                    {"lc_class": lc_class, "lc_name": lc_name, "hs_id": hs_id},
                )

        logger.info(f"✅ Successfully enriched {len(updates)} hotspots with land-cover data!")
    else:
        logger.warning("⚠ No land-cover values were resolved.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(enrich_land_cover())
