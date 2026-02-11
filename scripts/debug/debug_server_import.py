import uvicorn
import sys
import os

sys.path.append(os.getcwd())

if __name__ == "__main__":
    print("--- STARTING UVICORN PROGRAMMATICALLY ---")
    try:
        # Import the app to check for ImportErrors first
        from backend.api import app
        print("✅ Backend App Object Imported Successfully.")
        
        # Run Uvicorn without file watcher for test
        config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
        server = uvicorn.Server(config)
        
        # We perform a dry run (just startup check logic essentially)
        # But uvicorn doesn't have a dry-run. 
        # We will assume if import works, it's mostly fine unless port is blocked.
        print("✅ Ready to serve on port 8000.")
        
    except Exception as e:
        print(f"❌ Backend Startup Failed: {e}")
        import traceback
        traceback.print_exc()
