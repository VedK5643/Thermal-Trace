import asyncio
import logging
from sqlalchemy import text, NullPool
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format='%(message)s')

async def main():
    db_url = settings.get_database_url
    engine = create_async_engine(
        db_url, poolclass=NullPool,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}
    )
    
    async with engine.connect() as conn:
        print("=== POST-REBUILD VALIDATION ===")
        
        # 1. Total Rows & Nulls
        res = await conn.execute(text("""
            SELECT 
                COUNT(*) as total, 
                COUNT(DISTINCT (osm_type, osm_id)) as distinct_ids,
                COUNT(*) FILTER (WHERE latitude IS NULL OR longitude IS NULL) as null_coords,
                COUNT(*) FILTER (WHERE geometry IS NULL) as null_geom
            FROM osm_features
        """))
        total, distinct, null_c, null_g = res.first()
        print(f"Total rows: {total} (Expected: 80687)")
        print(f"Distinct identities: {distinct} (Expected: 80687)")
        print(f"Duplicates: {total - distinct} (Expected: 0)")
        print(f"NULL Coordinates: {null_c} (Expected: 0)")
        print(f"NULL Geometry: {null_g} (Expected: 0)")
        
        # 2. Type Counts
        res = await conn.execute(text("""
            SELECT 
                COUNT(*) FILTER (WHERE osm_type = 'node') as nodes,
                COUNT(*) FILTER (WHERE osm_type = 'way') as ways,
                COUNT(*) FILTER (WHERE osm_type = 'relation') as relations
            FROM osm_features
        """))
        nodes, ways, rels = res.first()
        print(f"Nodes: {nodes} (Expected: 15789)")
        print(f"Ways: {ways} (Expected: 64898)")
        print(f"Relations: {rels} (Expected: 0)")
        
        # 3. PostGIS Geometry Check
        res = await conn.execute(text("""
            SELECT 
                ST_SRID(geometry) as srid, 
                GeometryType(geometry) as geom_type 
            FROM osm_features LIMIT 1
        """))
        row = res.first()
        if row:
            srid, geom_type = row
            print(f"Geometry SRID: {srid} (Expected: 4326)")
            print(f"Geometry Type: {geom_type} (Expected: POINT)")
        
        # 4. Bounds
        res = await conn.execute(text("SELECT MIN(latitude), MAX(latitude), MIN(longitude), MAX(longitude) FROM osm_features"))
        bounds = res.first()
        print(f"Bounds: Lat({bounds[0]} to {bounds[1]}), Lon({bounds[2]} to {bounds[3]})")
        
        # 5. Top Categories
        res = await conn.execute(text("SELECT feature_type, COUNT(*) FROM osm_features GROUP BY feature_type ORDER BY COUNT(*) DESC LIMIT 5"))
        print("\nTop 5 Categories (DB):")
        for ft, count in res.fetchall():
            print(f"  {ft}: {count}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
