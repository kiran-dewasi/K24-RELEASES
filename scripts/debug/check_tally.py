import requests

def check_tally():
    url = "http://localhost:9000"
    print(f"Testing connection to Tally at {url}...")
    try:
        response = requests.get(url, timeout=2)
        print(f"✅ Tally is reachable! Status Code: {response.status_code}")
        print(f"Response: {response.text[:100]}...")
    except Exception as e:
        print(f"❌ Tally is NOT reachable: {e}")
        print("Make sure TallyPrime is running and 'Enable ODBC Server' is set to 'Yes' on port 9000.")

if __name__ == "__main__":
    check_tally()
