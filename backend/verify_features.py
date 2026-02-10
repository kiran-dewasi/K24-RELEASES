
import requests
import json
import sqlite3
import os

BASE_URL = "http://localhost:8000/api"
TOKEN = None

def get_token():
    """Login to get a fresh token"""
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", json={
            "email": "kittu@krishasales.com", 
            "password": "password123"
        })
        if resp.status_code == 200:
            return resp.json()['access_token']
        print(f"[X] Login Failed: {resp.text}")
        return None
    except Exception as e:
        print(f"[X] Backend Down: {e}")
        return None

def test_item_360(token):
    print("\n[INFO] Testing Item 360 View...")
    # First get an item ID
    try:
        # We need a valid item ID. Let's peek at DB or list items.
        # Check DB directly for an item ID
        conn = sqlite3.connect('../../k24_shadow.db') # Assuming running from backend/scripts/
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM items LIMIT 1")
        item = cursor.fetchone()
        conn.close()
        
        if not item:
            print("[WARN] No items in DB to test. Skipping.")
            return

        item_id, item_name = item
        print(f"   Target Item: {item_name} (ID: {item_id})")
        
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{BASE_URL}/items/{item_id}", headers=headers)
        
        if resp.status_code == 200:
            data = resp.json()
            # Check for 360 fields
            if 'stock_movements' in data or 'stats' in data:
                print("[OK] Item 360 Data: OK")
            else:
                print("[WARN] Item Data returned but missing 360 details.")
        else:
             print(f"[X] Item View Failed: {resp.status_code}")

    except Exception as e:
        print(f"[X] Item 360 Error: {e}")

def test_web_chat(token):
    print("\n[INFO] Testing Web Chat AI...")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "message": "Show me top selling items",
        "history": []
    }
    try:
        resp = requests.post(f"{BASE_URL}/chat/send", json=payload, headers=headers)
        if resp.status_code == 200:
            print(f"[OK] AI Response: {resp.json().get('response', '')[:50]}...")
        else:
            print(f"[X] Chat Failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"[X] Chat Connect Error: {e}")

if __name__ == "__main__":
    token = get_token()
    if token:
        test_item_360(token)
        test_web_chat(token)
