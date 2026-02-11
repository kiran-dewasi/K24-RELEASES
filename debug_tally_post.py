"""
Debug script to DIRECTLY invoke the Auto-Execution logic logic.
This bypasses the running API server to test Tally connection and logic in a fresh process.
"""
import asyncio
import os
import sys
from datetime import datetime

# Setup path
sys.path.append(os.getcwd())

from backend.services.auto_executor import process_with_auto_execution
from backend.database import get_db, Tenant, SessionLocal

async def test_direct_post():
    print("="*60)
    print("DEBUG: Direct Tally Post Test")
    print("="*60)
    
    # 1. Mock Bill Data (High Confidence)
    bill_data = {
        "party_name": "Ramesh Traders",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "invoice_number": "DBG-999",
        "total_amount": 5900.0,
        "items": [
            {"description": "Test Item", "quantity": 1, "rate": 5000, "amount": 5000}
        ],
        "subtotal": 5000.0,
        "tax": 900.0,
        "confidence": 0.99, # High confidence
        "voucher_type": "Purchase"
    }
    
    # 2. Force Enable Auto Post in DB for this session
    db = SessionLocal()
    tenant_id = "TENANT-12345"
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            print("Creating dummy tenant...")
            tenant = Tenant(id=tenant_id, company_name="Test Co", auto_post_to_tally=True)
            db.add(tenant)
        else:
            print(f"Found Tenant. Auto Post Setting: {tenant.auto_post_to_tally}")
            if not tenant.auto_post_to_tally:
                print("Enabling Auto Post...")
                tenant.auto_post_to_tally = True
        db.commit()
    except Exception as e:
        print(f"DB Setup Error: {e}")
        return
    finally:
        db.close()
        
    # 3. Call Logic
    print("\nCalling process_with_auto_execution...")
    result = await process_with_auto_execution(
        bill_data=bill_data,
        user_id=tenant_id,
        tenant_id=tenant_id,
        auto_post_enabled=True # Force Passed as True
    )
    
    # 4. Analyze Result
    print("\n" + "="*60)
    print(f"RESULT ACTION: {result['action']}")
    print("="*60)
    
    if result['action'] == 'auto_posted':
        print("✅ SUCCESS: Logic returned 'auto_posted'")
        tally_res = result.get('tally_result', {})
        print(f"Tally Result: {tally_res}")
        if tally_res.get('success'):
            print("🚀 Tally accepted the voucher!")
        else:
            print("⚠️ Logic tried to post, but Tally returned failure.")
            print(f"Error: {tally_res.get('error')}")
            
    elif result['action'] == 'auto_created':
        print("❌ FAILED: Logic returned 'auto_created' (Skipped Tally)")
        print("Possible reasons: auto_post_enabled was overridden or logic failure.")
        
    elif result['action'] == 'needs_review':
        print("⚠️ NEEDS REVIEW: Confidence was too low?")
        print(f"Confidence: {result.get('confidence')}")

if __name__ == "__main__":
    asyncio.run(test_direct_post())
