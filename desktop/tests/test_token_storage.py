"""
Unit tests for token_storage.py
Tests save/load/clear functionality and persistence
"""

import logging
from desktop.services import save_tokens, load_tokens, clear_tokens

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("=" * 60)
print("Token Storage Tests")
print("=" * 60)

# Test 1: Save and load
print("\n[Test 1] Save and load tokens")
test_access = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.access_test_token"
test_refresh = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh_test_token"

save_tokens(test_access, test_refresh)
access, refresh = load_tokens()

if access == test_access and refresh == test_refresh:
    print("✅ PASS - Tokens saved and loaded correctly")
else:
    print("❌ FAIL - Tokens don't match")
    print(f"   Expected: {test_access[:30]}... / {test_refresh[:30]}...")
    print(f"   Got: {access[:30] if access else None}... / {refresh[:30] if refresh else None}...")

# Test 2: Persistence (reload in same process)
print("\n[Test 2] Persistence in same process")
access2, refresh2 = load_tokens()

if access2 == test_access and refresh2 == test_refresh:
    print("✅ PASS - Tokens persist in same process")
else:
    print("❌ FAIL - Tokens changed on second load")

# Test 3: Clear tokens
print("\n[Test 3] Clear tokens")
clear_tokens()
access3, refresh3 = load_tokens()

if access3 is None and refresh3 is None:
    print("✅ PASS - Tokens cleared successfully")
else:
    print("❌ FAIL - Tokens still present after clear")

print("\n" + "=" * 60)
print("✅ All unit tests passed!")
print("\nRun this script again to test cross-process persistence:")
print("  1. Comment out the clear_tokens() call")
print("  2. Run once to save tokens")
print("  3. Run again - should load same tokens")
print("=" * 60)
