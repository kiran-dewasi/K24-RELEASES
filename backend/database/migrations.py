import sqlite3
import uuid
import os

def ensure_tenant_id_exists():
    """
    Ensure every user has a unique tenant_id and whatsapp fields
    """
    # Determine DB path (robust key for different CWDs)
    db_path = "k24_shadow.db"
    
    # Check if running from root or inner dictionary
    if not os.path.exists(db_path):
        # Check if we are in backend/ or similar
        potential_path = os.path.join(os.path.dirname(__file__), "..", "..", "k24_shadow.db")
        if os.path.exists(potential_path):
            db_path = os.path.abspath(potential_path)
    
    # Use ASCII for status to avoid Windows encoding issues
    print(f"Connecting to database at: {db_path}")
    
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check existing columns
        cursor.execute("PRAGMA table_info(users)")
        columns_info = cursor.fetchall()
        column_names = [col[1] for col in columns_info]
        
        # 1. Add tenant_id if missing
        if 'tenant_id' not in column_names:
            print("[INFO] Adding tenant_id column...")
            cursor.execute("ALTER TABLE users ADD COLUMN tenant_id TEXT")
            conn.commit()
        else:
            print("[OK] tenant_id column exists.")
            
        # 2. Add WhatsApp columns if missing
        if 'whatsapp_number' not in column_names:
            print("[INFO] Adding whatsapp columns...")
            cursor.execute("ALTER TABLE users ADD COLUMN whatsapp_number TEXT")
            conn.commit()
        
        # Re-check columns since we might have just added some
        cursor.execute("PRAGMA table_info(users)")
        columns_info = cursor.fetchall()
        column_names = [col[1] for col in columns_info]
            
        if 'whatsapp_connected' not in column_names:
             cursor.execute("ALTER TABLE users ADD COLUMN whatsapp_connected INTEGER DEFAULT 0")
        
        if 'whatsapp_qr_code' not in column_names:
             cursor.execute("ALTER TABLE users ADD COLUMN whatsapp_qr_code TEXT")
             
        if 'whatsapp_session_data' not in column_names:
             cursor.execute("ALTER TABLE users ADD COLUMN whatsapp_session_data TEXT")
             
        conn.commit()
        print("[OK] WhatsApp columns verified.")
        
        # 3. Generate tenant_ids for existing users without one
        cursor.execute("SELECT id, email FROM users WHERE tenant_id IS NULL OR tenant_id = ''")
        users_without_tenant = cursor.fetchall()
        
        for user_id, email in users_without_tenant:
            # Generate unique tenant ID
            tenant_id = f"TENANT-{uuid.uuid4().hex[:8].upper()}"
            
            cursor.execute("""
                UPDATE users 
                SET tenant_id = ?
                WHERE id = ?
            """, (tenant_id, user_id))
            
            print(f"[OK] Generated tenant_id for {email}: {tenant_id}")
        
        conn.commit()
        print("[SUCCESS] Database migration complete")
        
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
    finally:
        if conn:
            conn.close()

# Run migration
if __name__ == "__main__":
    ensure_tenant_id_exists()
