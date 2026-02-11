
from sqlalchemy import create_engine, inspect
from backend.database import DATABASE_URL

def debug_db():
    print(f"Connecting to: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    
    tables = inspector.get_table_names()
    print(f"Tables found: {tables}")
    
    if 'vouchers' in tables:
        columns = [c['name'] for c in inspector.get_columns('vouchers')]
        print(f"Columns in 'vouchers': {columns}")
    else:
        print("'vouchers' table not found!")

if __name__ == "__main__":
    debug_db()
