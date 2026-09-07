import asyncio
import sys
import logging
import urllib.request
import json
sys.path.append("e:\\VEDAGYA\\Thermal Trace\\Thermal-Trace\\backend")

from app.services.firms_status import firms_sync_manager
from app.db.session import init_db

logging.basicConfig(level=logging.INFO)

async def trigger_sync():
    print("Triggering forced FIRMS sync...")
    await init_db() # Ensure DB is connected/initialized if needed
    executed = await firms_sync_manager.execute_sync_if_needed(force=True)
    print(f"Sync executed: {executed}")
    
    print("\nFetching /api/v1/firms/status")
    try:
        with urllib.request.urlopen("http://127.0.0.1:8080/api/v1/firms/status") as res:
            status = json.loads(res.read().decode())
            print(json.dumps(status, indent=2))
    except Exception as e:
        print("Status fetch failed:", e)

    print("\nFetching /api/v1/hotspots?limit=10")
    try:
        with urllib.request.urlopen("http://127.0.0.1:8080/api/v1/hotspots?limit=10") as res:
            hotspots = json.loads(res.read().decode())
            print(f"Total Hotspots: {hotspots['pagination']['total']}")
            print(f"Returned items: {len(hotspots['data'])}")
            if hotspots['data']:
                print("First hotspot ID:", hotspots['data'][0]['id'])
                print("First hotspot ML Type:", hotspots['data'][0]['ml_type'])
    except Exception as e:
        print("Hotspots fetch failed:", e)

if __name__ == "__main__":
    asyncio.run(trigger_sync())
