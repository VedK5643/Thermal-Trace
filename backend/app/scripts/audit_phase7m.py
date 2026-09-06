import asyncio
import json
import logging
from collections import Counter
from datetime import datetime
from sqlalchemy import text, NullPool
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format='%(message)s')

async def main():
    # 1. Load JSON
    with open("data/ml/osm_industrial_india_raw.json", "r") as f:
        data = json.load(f)
    json_elements = data.get("elements", [])
    
    json_identities = set()
    json_duplicates = 0
    json_feature_types = set()
    
    for e in json_elements:
        ident = (e['type'], e['id'])
        if ident in json_identities:
            json_duplicates += 1
        json_identities.add(ident)
        
        tags = e.get("tags", {})
        if 'power' in tags: json_feature_types.add(f"power_{tags['power']}")
        elif 'landuse' in tags: json_feature_types.add(f"landuse_{tags['landuse']}")
        elif 'man_made' in tags: json_feature_types.add(f"man_made_{tags['man_made']}")
        elif 'industrial' in tags: json_feature_types.add(f"industrial_{tags['industrial']}")

    # 2. Connect to DB
    db_url = settings.get_database_url
    engine = create_async_engine(
        db_url, poolclass=NullPool,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}
    )
    
    async with engine.connect() as conn:
        print("=== DB STATS ===")
        # Row counts and distinct counts
        res = await conn.execute(text("SELECT COUNT(*), COUNT(DISTINCT (osm_type, osm_id)), COUNT(*) FILTER (WHERE latitude IS NULL OR longitude IS NULL) FROM osm_features"))
        total_rows, distinct_rows, null_coords = res.first()
        print(f"Total Rows: {total_rows}")
        print(f"Distinct (osm_type, osm_id): {distinct_rows}")
        print(f"Duplicates: {total_rows - distinct_rows}")
        print(f"NULL Coordinates: {null_coords}")
        
        # Bounds
        res = await conn.execute(text("SELECT MIN(latitude), MAX(latitude), MIN(longitude), MAX(longitude) FROM osm_features"))
        bounds = res.first()
        print(f"Bounds: Lat({bounds[0]} to {bounds[1]}), Lon({bounds[2]} to {bounds[3]})")
        
        # Provenance / imported_at
        res = await conn.execute(text("SELECT MIN(imported_at), MAX(imported_at) FROM osm_features"))
        min_import, max_import = res.first()
        print(f"Import Date Range: {min_import} to {max_import}")
        
        # Feature types
        res = await conn.execute(text("SELECT feature_type, COUNT(*) FROM osm_features GROUP BY feature_type ORDER BY COUNT(*) DESC"))
        db_features = res.fetchall()
        print(f"\n=== DB FEATURE TYPES ({len(db_features)} distinct) ===")
        db_feature_names = set()
        for ft, count in db_features:
            print(f"  {ft}: {count}")
            db_feature_names.add(ft)
            
        # 3. Compare JSON vs DB identities
        print("\n=== IDENTITY COMPARISON ===")
        res = await conn.execute(text("SELECT osm_type, osm_id FROM osm_features"))
        db_identities = set()
        for row in res.fetchall():
            # SQLAlchemy might return BigInteger as int
            db_identities.add((row[0], int(row[1])))
            
        json_in_db = json_identities.intersection(db_identities)
        db_not_in_json = db_identities - json_identities
        json_not_in_db = json_identities - db_identities
        
        print(f"JSON distinct identities: {len(json_identities)}")
        print(f"JSON duplicates: {json_duplicates}")
        print(f"JSON identities in DB: {len(json_in_db)}")
        print(f"JSON identities missing from DB: {len(json_not_in_db)}")
        print(f"DB rows NOT in JSON: {len(db_not_in_json)}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
