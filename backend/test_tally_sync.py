import requests
import time
import datetime

def test_small_sync():
    """Test with 1 day data"""
    # Using today's date for a small sync test
    today = datetime.date.today().strftime("%Y%m%d")
    
    xml = f'''<ENVELOPE>
        <HEADER>
            <VERSION>1</VERSION>
            <TALLYREQUEST>Export</TALLYREQUEST>
            <TYPE>Data</TYPE>
            <ID>DayBook</ID>
        </HEADER>
        <BODY>
            <DESC>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    <SVFROMDATE type="Date">{today}</SVFROMDATE>
                    <SVTODATE type="Date">{today}</SVTODATE>
                </STATICVARIABLES>
            </DESC>
        </BODY>
    </ENVELOPE>'''
    
    try:
        start = time.time()
        print(f"Sending small sync request to http://localhost:9000...")
        response = requests.post(
            "http://localhost:9000",
            data=xml,
            timeout=30
        )
        duration = time.time() - start
        if response.status_code == 200:
            print(f"Small sync SUCCESS in {duration:.2f}s")
            print(f"Response size: {len(response.content)} bytes")
            return True
        else:
            print(f"Small sync FAILED with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Small sync FAILED: {e}")
        return False

def test_large_sync():
    """Test with 3 months data"""
    # 3 months range
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=90)
    
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    
    xml = f'''<ENVELOPE>
        <HEADER>
            <VERSION>1</VERSION>
            <TALLYREQUEST>Export</TALLYREQUEST>
            <TYPE>Data</TYPE>
            <ID>DayBook</ID>
        </HEADER>
        <BODY>
            <DESC>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    <SVFROMDATE type="Date">{start_str}</SVFROMDATE>
                    <SVTODATE type="Date">{end_str}</SVTODATE>
                </STATICVARIABLES>
            </DESC>
        </BODY>
    </ENVELOPE>'''
    
    try:
        start = time.time()
        print(f"Sending large sync request ({start_str} to {end_str}) to http://localhost:9000...")
        response = requests.post(
            "http://localhost:9000",
            data=xml,
            timeout=30  # Using current timeout
        )
        duration = time.time() - start
        if response.status_code == 200:
            print(f"Large sync SUCCESS in {duration:.2f}s")
            print(f"Response size: {len(response.content)} bytes")
            return True
        else:
            print(f"Large sync FAILED with status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"Large sync FAILED: {e}")
        print(f"This confirms the issue is with large data requests")
        return False

# Run tests
print("=== TALLY SYNC DIAGNOSTIC TEST ===\n")

# Check simple connectivity first
try:
    requests.get("http://localhost:9000", timeout=5)
    print("Port 9000 is open (Tally might be running)")
except Exception as e:
    print(f"WARNING: Could not connect to localhost:9000 - {e}")

print("\nTest 1: Small data sync (1 day)")
small_ok = test_small_sync()

print("\nTest 2: Large data sync (3 months)")
large_ok = test_large_sync()

print("\n=== DIAGNOSIS ===")
if small_ok and not large_ok:
    print("Issue confirmed: Timeout/Memory problem with large datasets")
    print("Solution: Implement batching + increase timeout")
elif not small_ok:
    print("Issue confirmed: Basic connectivity problem")
    print("Solution: Fix Tally ODBC configuration")
else:
    print("Both tests passed (or failed uniquely) - see output above.")
