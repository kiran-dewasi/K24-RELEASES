"""
Verification script for device_service.py
Tests stability and persistence of device ID
"""

from desktop.services import get_device_id

print("=" * 60)
print("Device ID Verification Test")
print("=" * 60)

# Get device ID twice in the same run
print("\n1. First call to get_device_id():")
id1 = get_device_id()
print(f"   {id1}")

print("\n2. Second call to get_device_id() (same process):")
id2 = get_device_id()
print(f"   {id2}")

print(f"\n3. Stability check:")
if id1 == id2:
    print(f"   ✅ PASS - IDs are identical within same process")
else:
    print(f"   ❌ FAIL - IDs differ!")
    
print("\n" + "=" * 60)
print("Run this script again in a new process to verify persistence!")
print("=" * 60)
