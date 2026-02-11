"""
Debug script to DIRECTLY push a voucher to Tally.
Bypasses confidence scoring and API.
"""
import asyncio
import os
import sys
from datetime import datetime

# Setup path
sys.path.append(os.getcwd())

from backend.services.auto_executor import _push_to_tally_internal

async def test_tally_push_direct():
    print("="*60)
    print("DEBUG: Direct Tally Push Test")
    print("="*60)
    
    # 1. Mock Voucher Data (As expected by Tally Connector)
    voucher = {
        "voucher_type": "Purchase",
        "party_name": "Ramesh Traders", # Must exist or be created
        "date": datetime.now().strftime("%Y%m%d"), # YYYYMMDD
        "narration": "Debug Direct Push",
        "line_items": [
            {"name": "PVC Pipe 4inch", "quantity": 10, "rate": 500, "amount": 5000}
        ],
        "total_amount": 5900
    }
    
    print(f"Pushing Voucher: {voucher['party_name']} - {voucher['total_amount']}")
    
    # 2. Call Push Logic
    # Passing tenant_id as None if logic handles it
    result = await _push_to_tally_internal(voucher, tenant_id="TENANT-12345")
    
    # 3. Analyze Result
    print("\n" + "="*60)
    print(f"RESULT SUCCESS: {result.get('success')}")
    print("="*60)
    
    if result.get('success'):
        print("✅ TALLY ACCEPTED VOUCHER!")
        print(f"Response: {result.get('tally_response')}")
    else:
        print("❌ TALLY FAILED.")
        print(f"Error: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(test_tally_push_direct())
