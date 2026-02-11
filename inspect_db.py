from sqlalchemy import create_engine, inspect
import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB = "sqlite:///./k24_shadow.db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB)

engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

try:
    columns = inspector.get_columns('chat_history')
    print("Columns in chat_history:")
    for column in columns:
        print(f"- {column['name']}")
except Exception as e:
    print(f"Error inspecting chat_history: {e}")
