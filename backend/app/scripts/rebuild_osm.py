import sys
import json
import asyncio
import logging
from collections import Counter
from sqlalchemy import text, NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def derive_feature_type(tags):
    if 'power' in tags: return f"power_{tags['power']}"
    if 'landuse' in tags: return f"landuse_{tags['landuse']}"
    if 'man_made' in tags: return f"man_made_{tags['man_made']}"
    if 'industrial' in tags: return f"industrial_{tags['industrial']}"
    return "unknown"

async def main():
    json_path = "data/ml/osm_industrial_india_raw.json"
    logger.info(f"Loading {json_path}...")
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON: {e}")
        sys.exit(1)

    elements = data.get("elements", [])
    logger.info(f"Loaded {len(elements)} elements.")
    
    # 1. Parse into staging list
    staging_rows = []
    identities = set()
    node_count = 0
    way_count = 0
    
    for e in elements:
        osm_type = e["type"]
        osm_id = e["id"]
        
        ident = (osm_type, osm_id)
        if ident in identities:
            logger.error(f"Duplicate identity found: {ident}")
            sys.exit(1)
        identities.add(ident)
        
        if osm_type == "node":
            node_count += 1
            lat = e.get("lat")
            lon = e.get("lon")
        elif osm_type == "way":
            way_count += 1
            lat = e.get("center", {}).get("lat")
            lon = e.get("center", {}).get("lon")
        else:
            logger.error(f"Unexpected OSM type: {osm_type}")
            sys.exit(1)
            
        if lat is None or lon is None:
            logger.error(f"Missing coordinates for {ident}")
            sys.exit(1)
            
        tags = e.get("tags", {})
        ftype = derive_feature_type(tags)
        
        staging_rows.append({
            "id": f"{osm_type}/{osm_id}",
            "osm_type": osm_type,
            "osm_id": osm_id,
            "feature_type": ftype,
            "name": tags.get("name"),
            "latitude": float(lat),
            "longitude": float(lon),
            "raw_tags": json.dumps(tags)
        })

    # 2. In-Memory Validations
    if len(staging_rows) != 80687:
        logger.error(f"Expected 80687 rows, got {len(staging_rows)}")
        sys.exit(1)
    if node_count != 15789:
        logger.error(f"Expected 15789 nodes, got {node_count}")
        sys.exit(1)
    if way_count != 64898:
        logger.error(f"Expected 64898 ways, got {way_count}")
        sys.exit(1)
    if len(identities) != 80687:
        logger.error("Identities are not unique.")
        sys.exit(1)
        
    logger.info("In-memory validation PASSED. Proceeding to atomic DB swap.")
    
    # 3. DB Atomic Swap
    db_url = settings.get_database_url
    engine = create_async_engine(
        db_url,
        poolclass=NullPool,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    
    insert_query = text("""
        INSERT INTO osm_features (id, osm_type, osm_id, feature_type, name, latitude, longitude, raw_tags, geometry, imported_at)
        VALUES (:id, :osm_type, :osm_id, :feature_type, :name, :latitude, :longitude, CAST(:raw_tags AS jsonb), ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326), CURRENT_TIMESTAMP)
    """)
    
    async with session_factory() as session:
        async with session.begin():
            logger.info("TRUNCATING osm_features...")
            await session.execute(text("TRUNCATE TABLE osm_features"))
            
            logger.info("INSERTING 80,687 records...")
            # We can insert in one go or batches. 80k is small enough for executemany, but 
            # asyncpg might have param limits. Safe to chunk.
            chunk_size = 5000
            for i in range(0, len(staging_rows), chunk_size):
                chunk = staging_rows[i:i+chunk_size]
                await session.execute(insert_query, chunk)
                
            logger.info("Committing transaction...")
            
    await engine.dispose()
    logger.info("Atomic DB swap complete!")

if __name__ == "__main__":
    asyncio.run(main())
