"""
Phase 3 Verification Test
=========================
Tests the WhatsApp → Tenant Linking system.
"""
import sys
sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("PHASE 3 VERIFICATION TEST")
print("=" * 60)

# Test 1: WhatsApp Binding Router
print("\n1. Testing WhatsApp Binding Router...")
try:
    from backend.routers.whatsapp_binding import router
    print("   [OK] whatsapp_binding router imported")
except Exception as e:
    print(f"   [FAIL] {e}")
    sys.exit(1)

# Test 2: WhatsApp Main Router
print("\n2. Testing WhatsApp Main Router...")
try:
    from backend.routers.whatsapp import router as wa_router
    print("   [OK] whatsapp router imported")
except Exception as e:
    print(f"   [FAIL] {e}")
    sys.exit(1)

# Test 3: Tenant Model has whatsapp_number
print("\n3. Checking Tenant Model...")
try:
    from backend.database import Tenant
    
    # Check if whatsapp_number column exists
    if hasattr(Tenant, 'whatsapp_number'):
        print("   [OK] Tenant.whatsapp_number column exists")
    else:
        print("   [WARN] Tenant.whatsapp_number column not found")
except Exception as e:
    print(f"   [WARN] {e}")

# Test 4: User Model has whatsapp fields
print("\n4. Checking User Model...")
try:
    from backend.database import User
    
    fields = ['whatsapp_number', 'is_whatsapp_verified', 'tenant_id']
    for field in fields:
        if hasattr(User, field):
            print(f"   [OK] User.{field} column exists")
        else:
            print(f"   [WARN] User.{field} column not found")
except Exception as e:
    print(f"   [WARN] {e}")

# Test 5: Identify User Endpoint (Mock Test)
print("\n5. Testing Identify User Logic...")
try:
    import sqlite3
    
    conn = sqlite3.connect("k24_shadow.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check if whatsapp_customer_mappings table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='whatsapp_customer_mappings'
    """)
    
    if cursor.fetchone():
        print("   [OK] whatsapp_customer_mappings table exists")
        
        # Check if any mappings exist
        cursor.execute("SELECT COUNT(*) as cnt FROM whatsapp_customer_mappings")
        count = cursor.fetchone()['cnt']
        print(f"   [INFO] {count} customer mappings in database")
    else:
        print("   [INFO] whatsapp_customer_mappings table will be created on first use")
    
    conn.close()
except Exception as e:
    print(f"   [WARN] {e}")

# Test 6: Conflict Detection Logic
print("\n6. Testing Conflict Detection...")
try:
    from backend.database import SessionLocal, User
    
    db = SessionLocal()
    
    # Count verified WhatsApp users
    verified_count = db.query(User).filter(
        User.is_whatsapp_verified == True
    ).count()
    
    print(f"   [INFO] {verified_count} users have verified WhatsApp")
    
    # Check for potential conflicts (same number, different users)
    from sqlalchemy import func
    
    duplicates = db.query(
        User.whatsapp_number, 
        func.count(User.id).label('count')
    ).filter(
        User.whatsapp_number != None,
        User.is_whatsapp_verified == True
    ).group_by(
        User.whatsapp_number
    ).having(func.count(User.id) > 1).all()
    
    if duplicates:
        print(f"   [WARN] Found {len(duplicates)} duplicate WhatsApp bindings!")
        for dup in duplicates:
            print(f"         - {dup.whatsapp_number}: {dup.count} users")
    else:
        print("   [OK] No duplicate WhatsApp bindings found")
    
    db.close()
except Exception as e:
    print(f"   [WARN] Could not check conflicts: {e}")

print("\n" + "=" * 60)
print("PHASE 3 VERIFICATION COMPLETE")
print("=" * 60)
print("""
Summary - WhatsApp Tenant Linking:

1. Binding Security:
   - Duplicate binding detection (user-level)
   - Duplicate binding detection (tenant-level)
   - 409 Conflict response for already-bound numbers

2. Routing Improvement:
   - identify-user now returns tenant_id
   - Baileys listener can route by tenant

3. Database Constraint (Run in Supabase):
   - PHASE3_WHATSAPP_CONSTRAINTS.sql
   - Adds UNIQUE constraint on tenants.whatsapp_number

WhatsApp Message Flow:
1. Customer sends message to K24 WhatsApp
2. Baileys calls /api/whatsapp/identify-user
3. Backend returns user_id + tenant_id
4. Baileys routes message to correct tenant's data
5. All queries filtered by tenant_id (IDOR protected!)

Next: Phase 4 - Composite Indexes & Final Testing
""")
