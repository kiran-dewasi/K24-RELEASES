from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB = "sqlite:///./k24_shadow.db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB)

print(f"Connecting to: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as connection:
        # Use CASCADE to handle dependencies
        print("Executing: DROP TABLE IF EXISTS chat_history CASCADE")
        connection.execute(text("DROP TABLE IF EXISTS chat_history CASCADE"))
        connection.commit()
    print("Table dropped successfully.")
except Exception as e:
    print(f"Error dropping table: {e}")
