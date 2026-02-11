"""
Test script for bulk bill processing.
Demonstrates parallel processing of multiple invoices.
"""

import os
from dotenv import load_dotenv
from backend.services.bulk_processor import process_bills_sync

load_dotenv()

def main():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not set")
        return
    
    # Test files (should exist from generate_invoice_suite.py)
    test_files = [
        "test_invoice_8items.jpg",
        "test_invoice_10items.jpg",
        "test_invoice_12items.jpg",
        "test_invoice_15items.jpg",
    ]
    
    # Filter to only existing files
    existing_files = [f for f in test_files if os.path.exists(f)]
    
    if not existing_files:
        print("No test invoice files found. Run backend/generate_invoice_suite.py first.")
        return
    
    print(f"Found {len(existing_files)} test invoices")
    print("Starting bulk processing...")
    
    result = process_bills_sync(
        image_paths=existing_files,
        user_id="test_user",
        api_key=api_key,
        max_concurrent=3  # Conservative to avoid rate limits
    )
    
    print("\n" + "=" * 50)
    print("BULK PROCESSING RESULTS")
    print("=" * 50)
    print(f"Total Bills: {result['total_bills']}")
    print(f"Success: {result['success']}")
    print(f"Errors: {result['errors']}")
    print(f"Time: {result['elapsed_seconds']}s")
    print(f"Avg per bill: {result['avg_per_bill']}s")
    
    print("\nPer-bill breakdown:")
    for r in result['results']:
        status = r.get('status', 'unknown')
        img = r.get('image', 'unknown')
        if status == 'success':
            print(f"  [OK] {img}: {r.get('items_count', 0)} items, confidence={r.get('confidence', 0):.2f}")
        else:
            print(f"  [ERR] {img}: {r.get('error', 'unknown error')}")

if __name__ == "__main__":
    main()
