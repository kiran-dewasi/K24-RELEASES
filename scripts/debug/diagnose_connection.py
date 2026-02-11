import requests
import sys

def test_url(url):
    print(f"Testing {url}...")
    try:
        response = requests.get(url, timeout=2)
        print(f"✅ Success! Status: {response.status_code}")
        print(f"Response: {response.text[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

print("--- DIAGNOSING TALLY CONNECTION ---")
v4 = test_url("http://127.0.0.1:9000")
print("-" * 30)
localhost = test_url("http://localhost:9000")

if v4 and not localhost:
    print("\nCONCLUSION: 'localhost' resolution is broken. Use '127.0.0.1'.")
elif not v4 and not localhost:
    print("\nCONCLUSION: Tally is listening but rejecting HTTP requests (Check Firewall or Auth).")
else:
    print("\nCONCLUSION: Both work. The issue might be intermittent or specific to the original script context.")
