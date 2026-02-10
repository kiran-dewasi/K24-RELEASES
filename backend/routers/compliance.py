from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db, Voucher, AuditLog
from backend.compliance.audit_service import AuditService
from backend.compliance.engine import ComplianceEngine
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/compliance", tags=["compliance"])

class AuditLogResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    user_id: str
    action: str
    timestamp: datetime
    old_value: Optional[str]
    new_value: Optional[str]
    reason: str

    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    high_value_count: int
    backdated_count: int
    weekend_count: int
    pending_tds: float

@router.get("/audit-logs", response_model=List[AuditLogResponse])
def get_audit_logs(entity_id: Optional[str] = None, db: Session = Depends(get_db)):
    if entity_id:
        return AuditService.get_logs_for_entity(db, "Voucher", entity_id)
    return AuditService.get_all_logs(db)

@router.get("/dashboard-stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    engine = ComplianceEngine(db)
    
    # High Value (> 2L)
    high_value = db.query(Voucher).filter(Voucher.amount > 200000).count()
    
    # Backdated (Flagged)
    backdated = db.query(Voucher).filter(Voucher.is_backdated == True).count()
    
    # Weekend
    weekend = db.query(Voucher).filter(Voucher.is_weekend_entry == True).count()
    
    # Pending TDS (Mock calculation)
    # Sum of amounts where tds_section is set
    tds_vouchers = db.query(Voucher).filter(Voucher.tds_section != None).all()
    total_tds = sum([engine.calculate_tds_liability(v.amount, v.tds_section) for v in tds_vouchers])
    
    return {
        "high_value_count": high_value,
        "backdated_count": backdated,
        "weekend_count": weekend,
        "pending_tds": total_tds
    }

@router.post("/run-scan")
def run_compliance_scan(db: Session = Depends(get_db)):
    engine = ComplianceEngine(db)
    results = engine.run_forensic_scan()
    return {"status": "success", "results": results}
