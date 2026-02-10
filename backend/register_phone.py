
import sqlite3

import os

def register_whatsapp_user(phone_number, tenant_id):
    # Connect to DB in parent directory
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'k24_shadow.db')
    print(f"Connecting to DB at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if tenant exists
    cursor.execute("SELECT id FROM tenants WHERE id = ?", (tenant_id,))
    if not cursor.fetchone():
        print(f"Creating tenant {tenant_id}...")
        cursor.execute("INSERT OR IGNORE INTO tenants (id, company_name, created_at) VALUES (?, 'Default Tenant', CURRENT_TIMESTAMP)", (tenant_id,))

    # Update USER with this phone number (assuming default user exists)
    # We will try to update the default user 'kittu@krishasales.com' first
    print(f"Linking {phone_number} to tenant {tenant_id}...")
    
    cursor.execute("""
        UPDATE users 
        SET whatsapp_number = ?, whatsapp_connected = 1, tenant_id = ?
        WHERE email = 'kittu@krishasales.com'
    """, (phone_number, tenant_id))
    
    if cursor.rowcount == 0:
        # If no user found, create one
        print("User not found, creating new user...")
        # Use an integer ID or let it autoincrement
        cursor.execute("""
            INSERT INTO users (email, full_name, role, tenant_id, whatsapp_number, whatsapp_connected)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('kittu@krishasales.com', 'Kittu', 'admin', tenant_id, phone_number, 1))

    # Also register in the mappings table if it exists (for Supabase routing)
    try:
        cursor.execute("CREATE TABLE IF NOT EXISTS whatsapp_mappings (phone_number TEXT PRIMARY KEY, tenant_id TEXT, user_id TEXT)")
        cursor.execute("INSERT OR REPLACE INTO whatsapp_mappings (phone_number, tenant_id, user_id) VALUES (?, ?, ?)", 
                       (phone_number, tenant_id, 'user_12345'))
        print("Updated whatsapp_mappings table.")
    except Exception as e:
        print(f"Mapping table warning: {e}")

    conn.commit()
    conn.close()
    print("[SUCCESS] Phone registered.")

if __name__ == "__main__":
    # Registering the number provided - using phone from k24_config.json
    # Format: country code + number without + sign
    register_whatsapp_user("917339906200", "TENANT-12345")
