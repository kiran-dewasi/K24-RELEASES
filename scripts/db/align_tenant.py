from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
connection = create_engine(DATABASE_URL).connect()

print("--- Checking Users ---")
result = connection.execute(text("SELECT id, email, username, tenant_id FROM users"))
for row in result:
    print(f"User: {row}")

# Update ALL users to the active tenant TENANT-12345 to unify visibility
# (Assuming single user environment for now)
print("\n--- Unifying Tenant to TENANT-12345 ---")
try:
    connection.execute(text("UPDATE users SET tenant_id = 'TENANT-12345'"))
    connection.execute(text("UPDATE whatsapp_mapping SET tenant_id = 'TENANT-12345'"))
    connection.commit()
    print("✅ Success: All users and mappings moved to TENANT-12345.")
except Exception as e:
    print(f"❌ Error: {e}")

connection.close()
