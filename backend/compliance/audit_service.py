from sqlalchemy.orm import Session
from backend.database import AuditLog, Voucher
import json
from datetime import datetime

class AuditService:
    @staticmethod
    def log_change(db: Session, entity_type: str, entity_id: str, action: str, 
                   user_id: str, old_data: dict, new_data: dict, reason: str):
        """
        Logs a change to the immutable AuditLog table.
        """
        # Convert dicts to JSON strings for storage
        old_json = json.dumps(old_data, default=str) if old_data else None
        new_json = json.dumps(new_data, default=str) if new_data else None
        
        log_entry = AuditLog(
            entity_type=entity_type,
            entity_id=str(entity_id),
            user_id=user_id,
            action=action,
            old_value=old_json,
            new_value=new_json,
            reason=reason,
            timestamp=datetime.now()
        )
        
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    @staticmethod
    def get_logs_for_entity(db: Session, entity_type: str, entity_id: str):
        return db.query(AuditLog).filter(
            AuditLog.entity_type == entity_type,
            AuditLog.entity_id == str(entity_id)
        ).order_by(AuditLog.timestamp.desc()).all()

    @staticmethod
    def get_all_logs(db: Session, limit: int = 100):
        return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
