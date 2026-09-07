import asyncio
import sys
import logging

sys.path.append("e:\\VEDAGYA\\Thermal Trace\\Thermal-Trace\\backend")

from app.integrations.firms.client import FIRMSClient
from app.integrations.firms.normalizer import parse_firms_csv
from app.core.config import settings

logging.basicConfig(level=logging.INFO)

async def main():
    client = FIRMSClient(map_key="5466cd62ba42d916d50fcd014d873499")
    source = "VIIRS_SNPP_NRT"
    bbox = "68.0,6.0,98.0,38.0"
    days = 1
    print(f"Fetching FIRMS for {source} with days={days}")
    
    try:
        csv_text = await client.fetch_csv(source=source, bbox=bbox, days=days)
        print("HTTP Response received. Length:", len(csv_text))
        print("First 200 chars:", repr(csv_text[:200]))
    except Exception as e:
        print("Fetch Exception:", e)
        return
        
    try:
        records = parse_firms_csv(csv_text, source)
        print(f"Parsed {len(records)} records")
        if records:
            print("First record:", records[0])
    except Exception as e:
        print("Parse Exception:", e)

if __name__ == "__main__":
    asyncio.run(main())
