from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from backend.database import get_db, UserSettings
from backend.auth import get_current_tenant_id  # If needed, or assume single tenant for L0

router = APIRouter(prefix="/api/setup", tags=["setup"])

class ConfigPayload(BaseModel):
    tally_url: str
    google_api_key: Optional[str] = ""
    auto_post_to_tally: Optional[bool] = False

@router.get("/status")
async def get_setup_status(db: Session = Depends(get_db)):
    """Get current configuration from SQLite"""
    # For L0 single-user desktop, fetch the first settings row
    settings = db.query(UserSettings).first()
    
    if not settings:
        return {
            "tally_url": "http://localhost:9000",
            "google_api_key": "",
            "auto_post_to_tally": False
        }
    
    return {
        "tally_url": settings.tally_url or "http://localhost:9000",
        "google_api_key": settings.google_api_key or "",
        "auto_post_to_tally": getattr(settings, 'auto_post_to_tally', False) or False
    }

@router.post("/save")
async def save_config(payload: ConfigPayload, db: Session = Depends(get_db)):
    """Save configuration to SQLite"""
    settings = db.query(UserSettings).first()
    
    if not settings:
        # Create default
        settings = UserSettings(
            tenant_id="default",
            tally_url=payload.tally_url, 
            google_api_key=payload.google_api_key,
            auto_post_to_tally=payload.auto_post_to_tally
        )
        db.add(settings)
    else:
        # Update
        settings.tally_url = payload.tally_url
        settings.google_api_key = payload.google_api_key
        settings.auto_post_to_tally = payload.auto_post_to_tally
        
    db.commit()
    db.refresh(settings)
    
    return {"success": True, "message": "Settings saved successfully."}

import requests

@router.get("/scan-tally")
def scan_tally_ports():
    """Scan local ports 9000-9005 for Tally instances"""
    found = []
    ports = range(9000, 9006)
    
    for port in ports:
        url = f"http://localhost:{port}"
        try:
            # Minimal check payload
            payload = "<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER><BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Companies</REPORTNAME></REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"
            response = requests.post(url, data=payload, timeout=0.5)
            
            if response.status_code == 200:
                found.append({"port": port, "url": url, "version": "Tally Prime"})
        except:
            continue
            
    return {"instances": found}
