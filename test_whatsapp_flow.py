"""
Test WhatsApp Integration Flow.
Simulates an incoming WhatsApp message with an invoice image.
"""
import requests
import base64
import json
import os
import time

BASE_URL = "http://localhost:8000"
IMAGE_PATH = "sample_invoice.png"
SENDER_PHONE = "917339906200" # Using the hardcoded override number for testing

def test_whatsapp_batch_flow():
    print("="*60)
    print("SIMULATING WHATSAPP BILL UPLOAD")
    print("="*60)
    
    # 1. Prepare Image
    if not os.path.exists(IMAGE_PATH):
        print(f"[ERROR] Image not found: {IMAGE_PATH}")
        return
        
    with open(IMAGE_PATH, "rb") as f:
        img_bytes = f.read()
        b64_img = base64.b64encode(img_bytes).decode('utf-8')
        
    print(f"[INFO] Loaded image: {len(b64_img)} bytes (base64)")
    
    # 2. Construct Payload
    payload = {
        "sender_phone": SENDER_PHONE,
        "batch_id": f"TEST-BATCH-{int(time.time())}",
        "images": [
            {
                "buffer": b64_img,
                "mimetype": "image/png",
                "filepath": "sample_invoice.png"
            }
        ]
    }
    
    # 3. Send Request
    url = f"{BASE_URL}/api/baileys/process-batch"
    headers = {
        "X-Baileys-Secret": "k24_baileys_secret", # Default secret
        "Content-Type": "application/json"
    }
    
    print(f"\n[HTTP] POST {url}")
    print("Sending request (this takes ~10-15s for Gemini Processing)...")
    
    start = time.time()
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        duration = time.time() - start
        
        print(f"\n[RESULT] Status: {resp.status_code}")
        print(f"Time Taken: {duration:.2f}s")
        
        if resp.status_code == 200:
            data = resp.json()
            print(json.dumps(data, indent=2))
            
            # Validation
            if data["status"] == "success":
                success_count = data["stats"]["success"]
                print(f"\n✅ SUCCESS! Processed {success_count} bill(s).")
                
                vouchers = data.get("vouchers", [])
                if vouchers:
                    v = vouchers[0]
                    print(f"   Party: {v.get('party_name')}")
                    print(f"   Amount: {v.get('total_amount')}")
                    print(f"   Action: {v.get('action')}")
                else:
                    print("   [WARNING] No vouchers returned in success response?")
            else:
                print(f"\n❌ FAILED. Error: {data.get('error')}")
        else:
            print(f"\n❌ HTTP FAILED: {resp.text}")
            
    except Exception as e:
        print(f"\n[CRITICAL] Request Failed: {e}")

if __name__ == "__main__":
    test_whatsapp_batch_flow()
