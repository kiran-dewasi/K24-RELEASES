import sys
import os
import logging

# Set up logging to capture WARNINGS and higher
# Force reconfiguration if already set by imports
logging.getLogger().handlers = []
logging.basicConfig(filename='sync_debug_warnings.log', level=logging.WARNING, filemode='w', format='%(asctime)s - %(levelname)s - %(message)s')

sys.path.insert(0, os.getcwd())
from backend.sync_engine import SyncEngine

def diagnose():
    print("Running diagnostic sync...")
    try:
        engine = SyncEngine()
        result = engine.pull_ledgers()
        print(f"Sync finished. Result: {result}")
        print("Check sync_debug_warnings.log")
    except Exception as e:
        print(f"Critical failure: {e}")

if __name__ == "__main__":
    diagnose()
