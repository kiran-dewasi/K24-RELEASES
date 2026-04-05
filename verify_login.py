import sys
import os
import httpx
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def run_test():
    payload = {
        "email": "ai.krisha24@gmail.com",
        "password": "Krisha@240124@#"
    }
    print("Testing login...")
    response = client.post("/api/auth/login", json=payload)
    print("Status code:", response.status_code)
    try:
        data = response.json()
        print("Response Keys:", data.keys())
        if "user" in data:
            print("User data:", data["user"])
            if data["user"].get("email") == payload["email"]:
                print("✅ Login successful")
            else:
                print("❌ Login successful but email mismatch")
        else:
            print("❌ Login failed, JSON response:", data)
    except Exception as e:
        print("Failed to decode JSON:", e, response.text)

if __name__ == "__main__":
    run_test()
