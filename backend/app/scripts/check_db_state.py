import asyncio
import logging
from sqlalchemy import text, NullPool
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format='%(message)s')

async def main():
    db_url = settings.get_database_url
    engine = create_async_engine(
        db_url,
        poolclass=NullPool,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}
    )
    
    async with engine.connect() as conn:
        print("=== DATABASE STATE (osm_features) ===")
        
        # 1. Total Rows
        res = await conn.execute(text("SELECT COUNT(*) FROM osm_features"))
        print(f"Total rows: {res.scalar()}")
        
        # 2. Geographic Bounds
        res = await conn.execute(text("SELECT MIN(latitude), MAX(latitude), MIN(longitude), MAX(longitude) FROM osm_features"))
        bounds = res.first()
        print(f"Geographic Bounds: Lat({bounds[0]} to {bounds[1]}), Lon({bounds[2]} to {bounds[3]})")
        
        # 3. Target Categories
        res = await conn.execute(text("SELECT feature_type, COUNT(*) FROM osm_features GROUP BY feature_type ORDER BY COUNT(*) DESC LIMIT 10"))
        print("\nTop 10 Categories:")
        for row in res.fetchall():
            print(f"  {row[0]}: {row[1]}")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
