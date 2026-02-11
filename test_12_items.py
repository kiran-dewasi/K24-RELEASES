from backend.agent_gemini import extract_bill_data
import json
import os
from dotenv import load_dotenv

load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")

print("Testing 12-item invoice...")
data = extract_bill_data("test_invoice_12items.jpg", google_api_key)

if data.get("error"):
    print(f"Error: {data['error']}")
else:
    print(f"Items Found: {len(data.get('items', []))}/12")
    print(f"Confidence: {data.get('confidence', 0)}")
    if len(data.get('items', [])) == 12:
        print("[PASSED]")
    else:
        print("[FAILED]")
