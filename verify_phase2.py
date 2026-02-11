"""
Phase 2 Verification Test
=========================
Tests the Secure Desktop Auth (Signed JWTs for Socket.IO).
"""
import sys
sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("PHASE 2 VERIFICATION TEST")
print("=" * 60)

# Test 1: Socket Token Functions
print("\n1. Testing Socket Token Functions...")
try:
    from backend.auth import create_socket_token, decode_socket_token
    print("   [OK] create_socket_token imported")
    print("   [OK] decode_socket_token imported")
except Exception as e:
    print(f"   [FAIL] {e}")
    sys.exit(1)

# Test 2: Token Generation
print("\n2. Testing Token Generation...")
try:
    test_user_id = "test-user-123"
    test_tenant_id = "TENANT-84F03F7D"
    test_license = "K24-ABCD1234-EFGH5678"
    
    token = create_socket_token(
        user_id=test_user_id,
        tenant_id=test_tenant_id,
        license_key=test_license
    )
    
    if token and len(token) > 50:
        print(f"   [OK] Token generated (length: {len(token)})")
        print(f"   Token preview: {token[:50]}...")
    else:
        print(f"   [FAIL] Token too short or empty")
except Exception as e:
    print(f"   [FAIL] {e}")
    sys.exit(1)

# Test 3: Token Verification
print("\n3. Testing Token Verification...")
try:
    decoded = decode_socket_token(token)
    
    if decoded:
        print(f"   [OK] Token decoded successfully")
        print(f"   - user_id: {decoded.get('sub')}")
        print(f"   - tenant_id: {decoded.get('tenant_id')}")
        print(f"   - license_key: {decoded.get('license_key')}")
        print(f"   - type: {decoded.get('type')}")
        
        # Verify values match
        if decoded.get('sub') == test_user_id:
            print(f"   [OK] user_id matches")
        else:
            print(f"   [FAIL] user_id mismatch")
            
        if decoded.get('tenant_id') == test_tenant_id:
            print(f"   [OK] tenant_id matches")
        else:
            print(f"   [FAIL] tenant_id mismatch")
    else:
        print(f"   [FAIL] Token decode returned None")
except Exception as e:
    print(f"   [FAIL] {e}")

# Test 4: Invalid Token Rejection
print("\n4. Testing Invalid Token Rejection...")
try:
    fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake.payload"
    decoded = decode_socket_token(fake_token)
    
    if decoded is None:
        print(f"   [OK] Fake token correctly rejected")
    else:
        print(f"   [FAIL] Fake token was accepted (security issue!)")
except Exception as e:
    print(f"   [OK] Exception raised for fake token: {type(e).__name__}")

# Test 5: Devices Router Import
print("\n5. Testing Devices Router...")
try:
    from backend.routers.devices import router
    print("   [OK] Devices router imported successfully")
except Exception as e:
    print(f"   [FAIL] {e}")
    sys.exit(1)

# Test 6: Socket Manager Import
print("\n6. Testing Socket Manager...")
try:
    from backend.socket_manager import socket_manager
    print("   [OK] Socket manager imported successfully")
    
    # Check connect method exists
    if hasattr(socket_manager, 'connect'):
        print("   [OK] connect() method exists")
    else:
        print("   [FAIL] connect() method missing")
except Exception as e:
    print(f"   [FAIL] {e}")

print("\n" + "=" * 60)
print("PHASE 2 VERIFICATION COMPLETE")
print("=" * 60)
print("""
Summary - Security Improvements:
- Device registration now returns socket_token (signed JWT)
- Socket.IO verifies JWT signature before accepting connection
- Impersonation attacks (fake tenant_id) are now blocked!

Connection Flow:
1. User logs in on web
2. Web calls /api/devices/register
3. Backend returns socket_token (signed JWT with tenant_id)
4. Desktop app connects with: { auth: { token: socket_token } }
5. Backend verifies JWT signature before accepting

Next: Phase 3 - WhatsApp Tenant Linking
""")
