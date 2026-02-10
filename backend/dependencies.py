
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY_NAME = "x-api-key"
API_KEY = os.getenv("API_KEY", "k24-secret-key-123") 

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    # Allow if no auth for specific dev/local scenarios if needed, but strict by default
    # For now, stick to strict or loose based on env?
    # Keeping strict as per original code
    raise HTTPException(status_code=403, detail="Could not validate credentials")

# Also move get_db here or keep in database.py? 
# Usually get_db is in database.py.
