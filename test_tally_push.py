import asyncio
import sys
import os
import logging

# Ensure we can import from backend
sys.path.append(os.getcwd())

from backend.services.auto_executor import _push_to_tally_internal

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_push():
    print("\n🚀 Starting Tally Push Test Suite (Bypassing Gemini)...\n")
    
    # We use "SHREE GANESH TRADERS" as it exists in your DB.
    # Make sure "Jeera" exists as an Item, or auto-creation handles it.
    
    # --- TEST 1: PURCHASE VOUCHER ---
    print("------------------------------------------------")
    print("Testing PURCHASE Voucher Push...")
    voucher_purchase = {
        "voucher_type": "Purchase",
        "date": "20260131", # YYYYMMDD
        "party_name": "SHREE GANESH TRADERS",
        "narration": "TEST SCRIPT - AUTOMATED PURCHASE",
        "line_items": [
             {
                 "item_name": "Cumin Seeds (Jeera)", 
                 "qty": 10, 
                 "unit": "kgs", 
                 "rate": 250, 
                 "amount": 2500
             }
        ],
        "gst": {
            "cgst": 0, "sgst": 0  # Simple case first
        },
        "amount": 2500
    }
    
    try:
        res = await _push_to_tally_internal(voucher_purchase, "default")
        print(f"✅ Purchase Result: {res}")
    except Exception as e:
        print(f"❌ Purchase Failed: {e}")
        import traceback
        traceback.print_exc()


    # --- TEST 2: SALES VOUCHER ---
    print("\n------------------------------------------------")
    print("Testing SALES Voucher Push...")
    voucher_sales = {
        "voucher_type": "Sales",
        "date": "20260131",
        "party_name": "SHREE GANESH TRADERS", 
        "narration": "TEST SCRIPT - AUTOMATED SALE",
         "line_items": [
             {
                 "item_name": "Cumin Seeds (Jeera)", 
                 "qty": 5, 
                 "unit": "kgs", 
                 "rate": 300, 
                 "amount": 1500
             }
        ],
        "amount": 1500
    }
    
    try:
        res = await _push_to_tally_internal(voucher_sales, "default")
        print(f"✅ Sales Result: {res}")
    except Exception as e:
        print(f"❌ Sales Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_push())
