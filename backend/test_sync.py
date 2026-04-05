import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))

import logging
logging.basicConfig(level=logging.DEBUG, filename='test_sync_clean.log', filemode='w', encoding='utf-8')

from routers.sync import perform_sync_task
from database import SessionLocal

print("Running perform_sync_task directly... (logs go to test_sync_clean.log)")
db = SessionLocal()
try:
    perform_sync_task(db)
    print("Done!")
except Exception as e:
    print(f"Exception: {e}")
finally:
    db.close()
