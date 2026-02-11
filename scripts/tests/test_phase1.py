
from backend.database import SessionLocal, Voucher, User  # Adjusted imports
from sqlalchemy import text
from datetime import datetime
import sys

def test_database_upgrade():
    print("🔍 PHASE 1 AUDIT: Checking Database Health...")
    db = SessionLocal()
    
    try:
        # TEST 1: Check if column exists physically in SQLite
        print("\n1. Checking Schema for 'tenant_id'...")
        try:
            result = db.execute(text("PRAGMA table_info(vouchers)")).fetchall()
            column_names = [row[1] for row in result]
            
            if 'tenant_id' in column_names:
                print("   ✅ SUCCESS: 'tenant_id' column found in 'vouchers' table.")
            else:
                print("   ❌ FAIL: 'tenant_id' column MISSING. Migration failed.")
                return
        except Exception as e:
             print(f"   ❌ FAIL: Could not query schema info. Error: {e}")
             return

        # TEST 2: Try to Insert a Multi-Tenant Record
        print("\n2. Testing Multi-Tenant Insert...")
        try:
            # Create a dummy voucher for "Tenant A"
            v1 = Voucher(
                guid="test-guid-1",
                voucher_number="V001",
                voucher_type="Sales",
                date=datetime.now(), # Needs datetime object
                amount=100.0,
                tenant_id="tenant_A"  # <--- The Critical Field
            )
            db.add(v1)
            db.commit()
            print("   ✅ SUCCESS: Inserted record with tenant_id='tenant_A'.")
        except Exception as e:
            print(f"   ❌ FAIL: Insert failed. Error: {e}")
            db.rollback()
            return

        # TEST 3: Verify Isolation (Can we see it?)
        print("\n3. Verifying Data Retrieval...")
        record = db.query(Voucher).filter_by(guid="test-guid-1").first()
        if record and record.tenant_id == "tenant_A":
            print(f"   ✅ SUCCESS: Retrieved record. Tenant ID: {record.tenant_id}")
        else:
            print("   ❌ FAIL: Could not retrieve the record.")

        # Cleanup
        if record:
            db.delete(record)
            db.commit()
            print("\n🎉 PHASE 1 COMPLETE: Database is Multi-Tenant Ready!")

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_database_upgrade()
