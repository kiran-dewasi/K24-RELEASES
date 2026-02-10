
import sqlite3
import os
import logging
from passlib.context import CryptContext

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SelfHealing")

# Password Context (Must match auth.py)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DB_NAME = "k24_shadow.db"

def get_db_path():
    # Logic to find the DB relative to this file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, DB_NAME)

def run_self_healing():
    logger.info(" ❤️  Running Self-Healing Diagnostics...")
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        logger.warning(f"Database not found at {db_path}. Creating new...")
        # In a real app, we might let SQLAlchemy create it, but for raw speed/ensure:
        # We perform migration check below which will create tables.
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Ensure Critical Tables Exist
    tables = [
        ("tenants", """
            CREATE TABLE IF NOT EXISTS tenants (
                id VARCHAR NOT NULL PRIMARY KEY, 
                company_name VARCHAR, 
                tally_company_name VARCHAR, 
                whatsapp_number VARCHAR, 
                license_key VARCHAR, 
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """),
        ("users", """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email VARCHAR UNIQUE,
                username VARCHAR,
                hashed_password VARCHAR,
                full_name VARCHAR,
                role VARCHAR,
                company_id INTEGER,
                tenant_id VARCHAR,
                whatsapp_number VARCHAR,
                whatsapp_connected BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                is_verified BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME
            )
        """),
        ("whatsapp_customer_mappings", """
            CREATE TABLE IF NOT EXISTS whatsapp_customer_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR,
                customer_phone VARCHAR NOT NULL,
                customer_name VARCHAR,
                client_code VARCHAR,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, customer_phone)
            )
        """),
        ("whatsapp_routing_cache", """
            CREATE TABLE IF NOT EXISTS whatsapp_routing_cache (
                phone_number VARCHAR PRIMARY KEY,
                route_info TEXT,
                expires_at DATETIME
            )
        """)
    ]
    
    for table_name, schema_sql in tables:
        try:
            cursor.execute(f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if cursor.fetchone()[0] == 0:
                logger.info(f"🛠️  Table '{table_name}' missing. Creating...")
                cursor.execute(schema_sql)
            else:
                # Table exists, check for missing columns (Naive Migration)
                # Specifically checking 'whatsapp_customer_mappings' if it was created empty before
                pass 
        except Exception as e:
            logger.error(f"Failed to check table {table_name}: {e}")

    # 2. Ensure Admin User Exists & Is Valid
    email = "kittu@krishasales.com"
    default_pass = "password123"
    
    cursor.execute("SELECT id, hashed_password, tenant_id FROM users WHERE email = ?", (email,))
    user_row = cursor.fetchone()
    
    if not user_row:
        logger.info(f"👤 Default user {email} missing. Creating...")
        hashed = pwd_context.hash(default_pass)
        cursor.execute("""
            INSERT INTO users (email, username, full_name, role, tenant_id, hashed_password, is_active, is_verified)
            VALUES (?, ?, ?, ?, ?, ?, 1, 1)
        """, (email, "kittu", "Kittu Admin", "admin", "12345", hashed))
    else:
        # User exists, verify password matches 'password123' if we want to force reset in dev
        # Or just ensure tenant_id is set
        user_id, current_hash, tenant_id = user_row
        if not tenant_id:
            logger.info(f"🔧 Fixing missing Tenant ID for {email}")
            cursor.execute("UPDATE users SET tenant_id = ? WHERE id = ?", ("12345", user_id))
            
    conn.commit()
    conn.close()
    logger.info("✅ Self-Healing Complete. System Ready.")

if __name__ == "__main__":
    run_self_healing()
