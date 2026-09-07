import asyncio
import sys
sys.path.append("e:\\VEDAGYA\\Thermal Trace\\Thermal-Trace\\backend")

from sqlalchemy import select, func
from app.db.session import async_session_factory
from app.db.models.osm_feature import OSMFeature

async def test_osm():
    async with async_session_factory() as db:
        stmt = select(func.count(OSMFeature.id))
        res = await db.execute(stmt)
        print("Total OSM features in production database:", res.scalar())

if __name__ == "__main__":
    asyncio.run(test_osm())
