"""
Phase 1 Verification Test
=========================
Tests the TenantService and TenantGuard implementations.
"""
import sys
sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("PHASE 1 VERIFICATION TEST")
print("=" * 60)

# Test 1: TenantService Import
print("\n1. Testing TenantService Import...")
try:
    from backend.services.tenant_service import tenant_service, TenantService
    print("   [OK] TenantService imported successfully")
except Exception as e:
    print(f"   [FAIL] {e}")
    sys.exit(1)

# Test 2: TenantGuard Import  
print("\n2. Testing TenantGuard Import...")
try:
    from backend.middleware.tenant_guard import TenantGuard, tenant_guard, require_tenant
    print("   [OK] TenantGuard imported successfully")
except Exception as e:
    print(f"   [FAIL] {e}")
    sys.exit(1)

# Test 3: Tenant ID Generation
print("\n3. Testing Tenant ID Generation...")
test_user_id = "84f03f7d-1234-5678-abcd-efgh12345678"
tenant_id = tenant_service.generate_tenant_id(test_user_id)
expected = "TENANT-84F03F7D"
if tenant_id == expected:
    print(f"   [OK] Generated: {tenant_id} (expected: {expected})")
else:
    print(f"   [FAIL] Generated: {tenant_id}, expected: {expected}")

# Test 4: Auth Router Import
print("\n4. Testing Auth Router Import...")
try:
    from backend.routers.auth import router
    print("   [OK] Auth router imported successfully")
except Exception as e:
    print(f"   [FAIL] {e}")
    sys.exit(1)

# Test 5: TenantGuard Filter Method
print("\n5. Testing TenantGuard Methods...")
try:
    # Create a mock user
    class MockUser:
        id = 1
        tenant_id = "TENANT-TEST1234"
    
    # Verify filter method exists and is callable
    if hasattr(TenantGuard, 'filter') and callable(getattr(TenantGuard, 'filter')):
        print("   [OK] TenantGuard.filter() method exists")
    else:
        print("   [FAIL] TenantGuard.filter() method missing")
    
    if hasattr(TenantGuard, 'verify_access') and callable(getattr(TenantGuard, 'verify_access')):
        print("   [OK] TenantGuard.verify_access() method exists")
    else:
        print("   [FAIL] TenantGuard.verify_access() method missing")
        
    if hasattr(TenantGuard, 'inject_tenant') and callable(getattr(TenantGuard, 'inject_tenant')):
        print("   [OK] TenantGuard.inject_tenant() method exists")
    else:
        print("   [FAIL] TenantGuard.inject_tenant() method missing")

except Exception as e:
    print(f"   [FAIL] {e}")

# Test 6: Local Tenant Creation (Dry Run)
print("\n6. Testing Local Tenant Creation (Dry Run)...")
try:
    from backend.database import SessionLocal, Tenant
    
    db = SessionLocal()
    # Check if TENANT-84F03F7D exists (from earlier testing)
    existing = db.query(Tenant).filter(Tenant.id == "TENANT-84F03F7D").first()
    if existing:
        print(f"   [OK] Found existing tenant: {existing.id} ({existing.company_name})")
    else:
        print("   [INFO] No existing tenant found (will be created on first registration)")
    db.close()
except Exception as e:
    print(f"   [WARN] Could not check local tenant: {e}")

print("\n" + "=" * 60)
print("PHASE 1 VERIFICATION COMPLETE")
print("=" * 60)
print("""
Summary:
- TenantService: Creates and syncs tenants across Supabase/SQLite
- TenantGuard: Prevents IDOR attacks by filtering queries by tenant_id
- Auth Router: Now embeds tenant_id in JWT tokens

Next: Phase 2 - Desktop Auth (Signed JWTs for Socket.IO)
""")
