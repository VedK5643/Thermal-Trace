import asyncio
import sys
import logging
sys.path.append("e:\\VEDAGYA\\Thermal Trace\\Thermal-Trace\\backend")

from app.core.config import settings
from app.db.session import async_session_factory
from app.integrations.firms.service import FIRMSIngestionService

logging.basicConfig(level=logging.INFO)

async def test_sync():
    async with async_session_factory() as db:
        service = FIRMSIngestionService(db=db, map_key=settings.firms_map_key)
        res = await service.ingest_all_sources(
            sources=settings.firms_source_list,
            days=1, # using 1 day for testing to be fast
        )
        print("\n=== TRACE RESULTS ===")
        print(f"Sources Attempted: {res['sources_attempted']}")
        print(f"Sources Succeeded: {res['sources_succeeded']}")
        print(f"Sources Failed: {res['sources_failed']}")
        print(f"Total Fetched (Valid India rows): {res['total_fetched']}")
        print(f"Total Inserted: {res['total_inserted']}")
        print(f"Total Skipped: {res['total_skipped']}")
        print("Errors:")
        for e in res["errors"]:
            print(f" - {e['source']}: {e['error']}")

        print("\nPer Source Details:")
        for s in res["per_source"]:
            print(f" - {s['source']}: Fetched={s['fetched']} Inserted={s['inserted']} Skipped={s['skipped']}")

if __name__ == "__main__":
    asyncio.run(test_sync())
