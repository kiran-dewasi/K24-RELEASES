
import sqlite3
import os
import sys

# Ensure backend modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.database.encryption import encryptor

DB_FILE = "k24_shadow.db"

def is_encrypted(value):
    if not value: return False
    try:
        # Try to decrypt. If successful, it was encrypted.
        encryptor.decrypt(value)
        return True
    except Exception:
        return False

def migrate_data():
    if not os.path.exists(DB_FILE):
        print(f"Database {DB_FILE} not found.")
        return

    print("Starting Database Encryption Migration...")
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Encrypt Companies (phone, gstin, pan)
    print("Processing Companies...")
    cursor.execute("SELECT id, phone, gstin, pan FROM companies")
    companies = cursor.fetchall()
    
    company_updates = 0
    for comp in companies:
        updates = {}
        
        # Phone
        if comp['phone'] and not is_encrypted(comp['phone']):
            updates['phone'] = encryptor.encrypt(comp['phone'])
            
        # GSTIN
        if comp['gstin'] and not is_encrypted(comp['gstin']):
            updates['gstin'] = encryptor.encrypt(comp['gstin'])
            
        # PAN
        if comp['pan'] and not is_encrypted(comp['pan']):
            updates['pan'] = encryptor.encrypt(comp['pan'])
            
        if updates:
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [comp['id']]
            conn.execute(f"UPDATE companies SET {set_clause} WHERE id = ?", values)
            company_updates += 1
            
    print(f"  - Encrypted {company_updates} companies.")

    # 2. Encrypt Users (whatsapp_number)
    print("Processing Users...")
    cursor.execute("SELECT id, whatsapp_number FROM users")
    users = cursor.fetchall()
    
    user_updates = 0
    for user in users:
        updates = {}
        
        if user['whatsapp_number'] and not is_encrypted(user['whatsapp_number']):
            updates['whatsapp_number'] = encryptor.encrypt(user['whatsapp_number'])
            
        if updates:
            conn.execute("UPDATE users SET whatsapp_number = ? WHERE id = ?", (updates['whatsapp_number'], user['id']))
            user_updates += 1
            
    print(f"  - Encrypted {user_updates} users.")
    
    conn.commit()
    conn.close()
    print("Encryption Migration Complete!")

if __name__ == "__main__":
    migrate_data()
