from sqlalchemy.orm import Session
from backend.database import Voucher, AuditLog
from datetime import datetime, timedelta
from sqlalchemy import func

class ComplianceEngine:
    def __init__(self, db: Session):
        self.db = db

    def check_weekend_entry(self, date: datetime) -> bool:
        """Returns True if date is Saturday (5) or Sunday (6)"""
        return date.weekday() >= 5

    def check_backdated(self, voucher_date: datetime, created_at: datetime = None) -> bool:
        """
        Checks if a voucher is backdated by more than 2 days.
        If created_at is not provided, assumes current time (for new entries).
        """
        if not created_at:
            created_at = datetime.now()
        
        # If voucher date is significantly in the past compared to creation time
        # Allow 2 days buffer
        diff = created_at - voucher_date
        return diff.days > 2

    def check_high_value(self, amount: float, threshold: float = 200000) -> bool:
        """Flags transactions > 2 Lakhs (Cash limit)"""
        return amount > threshold

    def detect_duplicates(self, voucher_number: str, party_name: str, amount: float):
        """Checks for potential duplicates"""
        existing = self.db.query(Voucher).filter(
            Voucher.voucher_number == voucher_number,
            Voucher.party_name == party_name,
            Voucher.amount == amount
        ).first()
        return existing is not None

    def calculate_tds_liability(self, amount: float, section: str) -> float:
        """
        Simple TDS Calculator (Mock Logic for MVP)
        194C: 1% for Individual, 2% for Others (assuming 1% here)
        194J: 10%
        """
        rates = {
            "194C": 0.01,
            "194J": 0.10,
            "194H": 0.05,
            "194Q": 0.001
        }
        rate = rates.get(section, 0)
        return amount * rate

    def check_round_tripping(self, voucher: Voucher) -> bool:
        """
        Checks if there is a counter-transaction with the same party on the same day.
        If current is Receipt, look for Payment. If Payment, look for Receipt.
        """
        target_type = "Payment" if voucher.voucher_type == "Receipt" else "Receipt"
        
        # We only care about Receipts and Payments
        if voucher.voucher_type not in ["Receipt", "Payment"]:
            return False
            
        counter_txn = self.db.query(Voucher).filter(
            Voucher.party_name == voucher.party_name,
            Voucher.voucher_type == target_type,
            func.date(Voucher.date) == func.date(voucher.date),
            Voucher.id != voucher.id
        ).first()
        
        return counter_txn is not None

    def run_forensic_scan(self):
        """Scans all vouchers and updates flags"""
        vouchers = self.db.query(Voucher).all()
        results = {
            "weekend_entries": 0,
            "backdated_entries": 0,
            "high_value": 0,
            "round_trip_suspects": 0
        }
        
        for v in vouchers:
            # Weekend Check
            if v.date and self.check_weekend_entry(v.date):
                v.is_weekend_entry = True
                results["weekend_entries"] += 1
            
            # Backdated Check
            # Find the creation time from Audit Logs
            creation_log = self.db.query(AuditLog).filter(
                AuditLog.entity_type == "Voucher",
                AuditLog.entity_id == v.voucher_number,
                AuditLog.action == "CREATE"
            ).first()
            
            if creation_log:
                if self.check_backdated(v.date, creation_log.timestamp):
                    v.is_backdated = True
                    results["backdated_entries"] += 1
            
            # High Value Check
            if self.check_high_value(v.amount):
                results["high_value"] += 1
                
            # Round Trip Check
            if self.check_round_tripping(v):
                results["round_trip_suspects"] += 1
            
            self.db.commit()
        
        return results
