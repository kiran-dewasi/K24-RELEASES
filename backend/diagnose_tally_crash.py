"""
TALLY SYNC CRASH DIAGNOSTIC
============================
This script diagnoses WHY Tally goes offline during K24 sync.
Run this BEFORE attempting any fixes.
"""

import sys
import os
import time
import traceback

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 70)
print("TALLY SYNC CRASH DIAGNOSTIC - K24.ai System")
print("=" * 70)
print()

# ============================================================
# PHASE 1: Basic Connectivity Test
# ============================================================
print("[PHASE 1] Basic Connectivity Test")
print("-" * 50)

import requests

try:
    response = requests.get("http://localhost:9000", timeout=5)
    print(f"  Port 9000: OPEN (Tally responding)")
    print(f"  Response: {response.text[:100]}..." if len(response.text) > 100 else f"  Response: {response.text}")
except requests.exceptions.ConnectionError:
    print("  ERROR: Cannot connect to localhost:9000")
    print("  FIX: Ensure Tally is running with ODBC server enabled")
    sys.exit(1)
except Exception as e:
    print(f"  Port 9000: OPEN but got: {e}")

print()

# ============================================================
# PHASE 2: Check Current TallyConnector Configuration
# ============================================================
print("[PHASE 2] TallyConnector Configuration")
print("-" * 50)

try:
    from backend.tally_connector import TallyConnector, TALLY_API_URL, DEFAULT_COMPANY
    
    print(f"  Tally URL: {TALLY_API_URL}")
    print(f"  Default Company: {DEFAULT_COMPANY}")
    
    connector = TallyConnector()
    print(f"  Connector Timeout: {connector.timeout} seconds")
    print(f"  Company Name: {connector.company_name}")
    
    # Check if session exists (new fix)
    if hasattr(connector, 'session'):
        print(f"  Session: Using requests.Session (GOOD)")
    else:
        print(f"  Session: Using raw requests (NEEDS FIX - no retry logic)")
        
except Exception as e:
    print(f"  ERROR loading TallyConnector: {e}")
    traceback.print_exc()

print()

# ============================================================
# PHASE 3: Test Simple Tally Request
# ============================================================
print("[PHASE 3] Simple Tally Request Test")
print("-" * 50)

try:
    connector = TallyConnector()
    
    # Simple company info request
    xml = '''<ENVELOPE>
        <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
        <BODY>
            <EXPORTDATA>
                <REQUESTDESC>
                    <REPORTNAME>Company Info</REPORTNAME>
                </REQUESTDESC>
            </EXPORTDATA>
        </BODY>
    </ENVELOPE>'''
    
    start = time.time()
    response = connector.send_request(xml)
    duration = time.time() - start
    
    print(f"  Simple request: SUCCESS")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Response size: {len(response)} bytes")
    
except Exception as e:
    print(f"  Simple request: FAILED - {e}")

print()

# ============================================================
# PHASE 4: Test Ledger Fetch (Common Sync Operation)
# ============================================================
print("[PHASE 4] Ledger Fetch Test")
print("-" * 50)

try:
    connector = TallyConnector()
    
    start = time.time()
    ledgers = connector.fetch_ledgers()
    duration = time.time() - start
    
    if hasattr(ledgers, '__len__'):
        print(f"  Ledgers fetched: {len(ledgers)}")
    else:
        print(f"  Ledgers response type: {type(ledgers)}")
    
    print(f"  Duration: {duration:.2f}s")
    print(f"  Status: SUCCESS")
    
except Exception as e:
    print(f"  Ledger fetch: FAILED - {e}")
    traceback.print_exc()

print()

# ============================================================
# PHASE 5: Test Voucher Fetch (Often Causes Crashes)
# ============================================================
print("[PHASE 5] Voucher Fetch Test (Last 30 Days)")
print("-" * 50)

try:
    from datetime import datetime, timedelta
    
    connector = TallyConnector()
    
    to_date = datetime.now().strftime("%Y%m%d")
    from_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    
    print(f"  Date range: {from_date} to {to_date}")
    
    start = time.time()
    vouchers = connector.fetch_vouchers(from_date=from_date, to_date=to_date)
    duration = time.time() - start
    
    if hasattr(vouchers, '__len__'):
        print(f"  Vouchers fetched: {len(vouchers)}")
    else:
        print(f"  Vouchers response type: {type(vouchers)}")
    
    print(f"  Duration: {duration:.2f}s")
    print(f"  Status: SUCCESS")
    
except Exception as e:
    print(f"  Voucher fetch: FAILED - {e}")
    traceback.print_exc()

print()

# ============================================================
# PHASE 6: Test Stock Items Fetch
# ============================================================
print("[PHASE 6] Stock Items Fetch Test")
print("-" * 50)

try:
    connector = TallyConnector()
    
    start = time.time()
    items = connector.fetch_stock_items()
    duration = time.time() - start
    
    if hasattr(items, '__len__'):
        print(f"  Stock items fetched: {len(items)}")
    else:
        print(f"  Stock items response type: {type(items)}")
    
    print(f"  Duration: {duration:.2f}s")
    print(f"  Status: SUCCESS")
    
except Exception as e:
    print(f"  Stock items fetch: FAILED - {e}")
    traceback.print_exc()

print()

# ============================================================
# PHASE 7: Test Full Sync Engine (The Actual Sync Code Path)
# ============================================================
print("[PHASE 7] Sync Engine Test")
print("-" * 50)

try:
    from backend.sync_engine import SyncEngine
    
    sync_engine = SyncEngine()
    print(f"  SyncEngine loaded: SUCCESS")
    print(f"  Tally URL in engine: {sync_engine.tally.url}")
    print(f"  Tally timeout: {sync_engine.tally.timeout}s")
    
    # Test incremental sync (what happens on "Sync" button click)
    print()
    print("  Testing incremental_sync (last 24h)...")
    
    start = time.time()
    result = sync_engine.incremental_sync(since_hours=24)
    duration = time.time() - start
    
    print(f"  Result: {result}")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Status: SUCCESS")
    
except Exception as e:
    print(f"  SyncEngine test: FAILED - {e}")
    traceback.print_exc()

print()

# ============================================================
# PHASE 8: Memory Usage Check
# ============================================================
print("[PHASE 8] Memory Usage Check")
print("-" * 50)

try:
    import psutil
    
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    
    print(f"  Current process memory: {memory_mb:.2f} MB")
    
    if memory_mb > 500:
        print("  WARNING: High memory usage - may cause issues with large syncs")
    else:
        print("  Memory usage: OK")
        
except ImportError:
    print("  psutil not installed - skipping memory check")
except Exception as e:
    print(f"  Memory check failed: {e}")

print()

# ============================================================
# PHASE 9: Test Large Data Request (Stress Test)
# ============================================================
print("[PHASE 9] Large Data Stress Test (Full Year)")
print("-" * 50)

try:
    from datetime import datetime, timedelta
    
    connector = TallyConnector()
    
    # Full year range - likely to cause timeout on weak configs
    to_date = datetime.now().strftime("%Y%m%d")
    from_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
    
    print(f"  Date range: {from_date} to {to_date} (1 year)")
    print(f"  Timeout setting: {connector.timeout}s")
    print("  Fetching...")
    
    start = time.time()
    vouchers = connector.fetch_vouchers(from_date=from_date, to_date=to_date)
    duration = time.time() - start
    
    if hasattr(vouchers, '__len__'):
        print(f"  Vouchers fetched: {len(vouchers)}")
    else:
        print(f"  Vouchers response type: {type(vouchers)}")
    
    print(f"  Duration: {duration:.2f}s")
    print(f"  Status: SUCCESS - Large data handled OK")
    
except requests.exceptions.Timeout:
    print(f"  TIMEOUT after {connector.timeout}s")
    print("  DIAGNOSIS: Timeout issue confirmed!")
    print("  FIX: Increase timeout or implement pagination")
except Exception as e:
    print(f"  Large data test: FAILED - {e}")
    traceback.print_exc()

print()

# ============================================================
# PHASE 10: Check Tally Sync Service Status
# ============================================================
print("[PHASE 10] Tally Sync Service Status")
print("-" * 50)

try:
    from backend.services.tally_sync_service import tally_sync_service
    
    print(f"  Service instance: {tally_sync_service}")
    print(f"  Is running: {tally_sync_service.is_running}")
    print(f"  Active interval: {tally_sync_service.interval_active}s")
    print(f"  Idle interval: {tally_sync_service.interval_idle}s")
    print(f"  Stats: {tally_sync_service.sync_stats}")
    
except Exception as e:
    print(f"  Service check failed: {e}")

print()

# ============================================================
# SUMMARY
# ============================================================
print("=" * 70)
print("DIAGNOSTIC SUMMARY")
print("=" * 70)
print("""
If all tests above passed, the issue may be:
1. Frontend sync button calling a different endpoint
2. Multiple simultaneous sync requests
3. Network issues during specific operations
4. Tally-side configuration (check F12 > Advanced Configuration)

Next Steps:
1. Check the frontend sync button's API call
2. Review FastAPI logs during actual sync attempt
3. Check Tally's log files for errors
4. Try triggering sync from K24 app while watching this console

To test the actual sync endpoint, run:
  curl -X POST http://localhost:8000/api/sync/now
""")

print("Diagnostic complete!")
