import asyncio
import sys
sys.path.append("e:\\VEDAGYA\\Thermal Trace\\Thermal-Trace\\backend")

from app.services.firms_status import FIRMSSyncManager
from app.db.session import init_db

async def test_status_bug():
    print("Simulating Worker A (Background Sync Worker)...")
    worker_a = FIRMSSyncManager()
    await worker_a.initialize_from_db()
    
    # Worker A executes a sync and inserts 2411 records
    await worker_a.record_sync_success(inserted=2411)
    
    print("Worker A Status payload:")
    print("  observationsIngested:", worker_a.get_status_payload()["observationsIngested"])
    
    print("\nSimulating Worker B (API Request Worker)...")
    worker_b = FIRMSSyncManager()
    await worker_b.initialize_from_db()
    
    print("Worker B Status payload (Bug reproduced):")
    print("  observationsIngested:", worker_b.get_status_payload()["observationsIngested"])

if __name__ == "__main__":
    asyncio.run(test_status_bug())
