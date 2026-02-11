from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("No DATABASE_URL found.")
    exit(1)

connection = create_engine(DATABASE_URL).connect()

# Check current mapping
print("Checking current mapping...")
result = connection.execute(text("SELECT * FROM whatsapp_mapping WHERE whatsapp_number LIKE '%7339906200%'"))
for row in result:
    print(f"Before: {row}")

# Update to TENANT-12345
print("Updating to TENANT-12345...")
connection.execute(text("UPDATE whatsapp_mapping SET tenant_id = 'TENANT-12345' WHERE whatsapp_number LIKE '%7339906200%'"))
connection.commit()

# Verify
print("Verifying Update...")
result = connection.execute(text("SELECT * FROM whatsapp_mapping WHERE whatsapp_number LIKE '%7339906200%'"))
for row in result:
    print(f"After: {row}")

connection.close()
