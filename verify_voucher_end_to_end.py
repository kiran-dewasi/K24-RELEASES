import os
import sys

# Ensure backend can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.tally_engine import TallyEngine
import logging

logging.basicConfig(level=logging.INFO)

def main():
    print("Initializing Tally Engine for End-to-End Voucher Verification...")
    engine = TallyEngine("http://localhost:9000")
    
    # Generate dynamic voucher numbers so this works on subsequent runs without duplication errors
    import time
    timestamp = int(time.time())
    
    # 1. Test Purchase Voucher (Uses TallyObjectFactory.create_voucher_xml which contains our fix)
    vnum_purch = f"TEST-PURCH-{timestamp}"
    print(f"\n--- Testing Purchase Voucher (ID: {vnum_purch}) ---")
    purchase_payload = {
        "date": "20260315", # Sending to 2026
        "voucher_type": "Purchase",
        "voucher_number": vnum_purch,
        "party_name": "Test End To End Supplier",
        "items": [
            {
                "name": "FRESH TEST ITEM 123", # Crucial: Non-batch item
                "unit": "kg",
                "quantity": 25,
                "rate": 120,
                "godown": "Main Location"
                # Omitted batch on purpose, ensuring our fix avoids <BATCHNAME>
            }
        ]
    }
    
    resp_purchase = engine.process_purchase_request(purchase_payload)
    print("Purchase Response:", resp_purchase)
    
    # 2. Test Sales Voucher (Uses GoldenXMLBuilder)
    vnum_sales = f"TEST-SALE-{timestamp}"
    print(f"\n--- Testing Sales Voucher (ID: {vnum_sales}) ---")
    sales_payload = {
        "date": "20260315", # Sending to 2026
        "voucher_type": "Sales",
        "voucher_number": vnum_sales,
        "party_name": "Test End To End Customer",
        "items": [
            {
                "name": "FRESH TEST ITEM 123", 
                "unit": "kg",
                "quantity": 10,
                "rate": 150,
                "godown": "Main Location"
            }
        ]
    }
    
    resp_sales = engine.process_sales_request(sales_payload)
    print("Sales Response:", resp_sales)
    
    success = True
    if resp_purchase.get("status") != "success":
        print("❌ Purchase Voucher failed.")
        success = False
    
    if resp_sales.get("status") != "success":
        print("Sales Voucher failed.")
        success = False
        
    if success:
        print("\nEnd-to-End Verification Complete! Tally accepted the vouchers via our logic, confirming the BATCHALLOCATION fix for non-batch items.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nFailed! {e}")
        import traceback
        traceback.print_exc()
