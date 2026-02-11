import sys
import os

# Set PWD to project root for imports to work
sys.path.append(os.getcwd())

print("--- TESTING BACKEND STARTUP ---")

try:
    from backend.database import init_db, engine
    print(f"✅ Imported Database Module. Engine URL: {engine.url}")
    
    print("🔄 Running init_db()...")
    init_db()
    print("✅ init_db() completed successfully.")
    
except ImportError as e:
    print(f"❌ Import Error: {e}")
except Exception as e:
    print(f"❌ Runtime Error: {e}")
    import traceback
    traceback.print_exc()

print("-------------------------------")
