import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check_connection():
    db_url = os.getenv("DATABASE_URL")
    print(f"Testing connection to: {db_url.split('@')[-1]}") # Hide credentials
    
    try:
        conn = await asyncpg.connect(db_url)
        print("✅ Connection Successful!")
        
        # Check if tables exist
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        print("\nExisting Tables:")
        found_checkpoints = False
        for row in tables:
            print(f"- {row['table_name']}")
            if row['table_name'] == 'checkpoints':
                found_checkpoints = True
                
        if found_checkpoints:
            print("\n✅ LangGraph 'checkpoints' table found. Ready for persistence.")
        else:
            print("\n❌ 'checkpoints' table NOT found. Please run the SQL script in Supabase.")
            
        await conn.close()
        
    except Exception as e:
        print(f"\n❌ Connection Failed: {e}")
        print("Tip: Ensure 'Allow connections from all IP addresses' is enabled in Supabase Settings -> Network if running locally.")

if __name__ == "__main__":
    asyncio.run(check_connection())
