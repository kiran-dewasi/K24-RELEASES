# 🛡️ K24 Compliance & Audit System - Implementation Plan

## 1. Database Schema Changes (`backend/database.py`)

### New Table: `AuditLog`
This table is the immutable "Black Box" for all financial changes.
```python
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String)  # "Voucher", "Ledger"
    entity_id = Column(String)    # GUID or ID of the modified entity
    user_id = Column(String)      # "admin", "kiran", etc.
    action = Column(String)       # "CREATE", "UPDATE", "DELETE"
    timestamp = Column(DateTime, default=datetime.now)
    
    # The "What"
    old_value = Column(String, nullable=True)  # JSON dump of state before edit
    new_value = Column(String, nullable=True)  # JSON dump of state after edit
    
    # The "Why" (Mandatory)
    reason = Column(String, nullable=False)
```

### Updates to `Voucher` Table
```python
class Voucher(Base):
    # ... existing fields ...
    
    # Workflow Status
    status = Column(String, default="Draft")  # Draft, Checked, Verified
    
    # Compliance Flags
    tds_section = Column(String, nullable=True)  # e.g., "194C", "194J"
    gst_reconciled = Column(Boolean, default=False)
    is_backdated = Column(Boolean, default=False)
    is_weekend_entry = Column(Boolean, default=False)
```

## 2. Backend Architecture

### `AuditService` (`backend/compliance/audit_service.py`)
- Middleware to intercept all write operations.
- `log_change(db, entity, action, old_data, new_data, reason)`
- Ensures immutability (no delete endpoint for logs).

### `ComplianceEngine` (`backend/compliance/engine.py`)
- **Forensic Checks**:
    - `check_duplicates()`: Scans for duplicate invoice numbers.
    - `check_weekend_entries()`: Flags Sat/Sun transactions.
    - `check_round_tripping()`: Finds A->B (Pay) and B->A (Receipt) on same day.
- **TDS Logic**:
    - `calculate_tds_liability()`: Checks if payments > threshold (e.g., 30k for 194C).

### API Endpoints (`backend/routers/compliance.py`)
- `GET /compliance/audit-logs`: Fetch logs with filters.
- `GET /compliance/dashboard-stats`: High value txns, pending TDS, etc.
- `POST /compliance/verify-voucher`: Auditor action to change status.

## 3. Frontend Dashboard (`frontend/src/app/compliance/audit-dashboard/page.tsx`)

### UI Components
1.  **Compliance Grid**: Ag-Grid style table showing all vouchers with status flags.
2.  **Audit History Modal**: Shows "Diff" view (Old vs New) for a selected voucher.
3.  **Widgets**:
    - 🚨 **Red Flags**: Backdated, Weekend, High Value.
    - 📊 **TDS Tracker**: Pending liabilities.
    - 🔄 **GST Reconciliation**: Books vs GSTR-2B.

## 4. Implementation Steps

1.  **Schema Migration**: Update `database.py` and run `init_db()`.
2.  **Backend Logic**: Implement `AuditService` and `ComplianceEngine`.
3.  **API Layer**: Create routes in `compliance.py`.
4.  **Frontend**: Build the Dashboard and History View.
5.  **Integration**: Update `operations.py` to call `AuditService` on edits.

## 5. Verification Plan
- Create a voucher -> Edit it -> Check Audit Log.
- Create a backdated voucher -> Check "Red Flag" widget.
