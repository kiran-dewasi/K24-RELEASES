from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
connection = create_engine(DATABASE_URL).connect()

print("--- Updating User Tenant ---")
try:
    connection.execute(text("UPDATE users SET tenant_id = 'TENANT-12345'"))
    connection.commit()
    print("✅ Success: All users moved to TENANT-12345.")
except Exception as e:
    print(f"❌ Error: {e}")

connection.close()
