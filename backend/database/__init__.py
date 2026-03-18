"""
K24 Shadow Database
The high-speed local store that mirrors Tally.
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean, JSON, UniqueConstraint, Index

# ... (rest of imports)


from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Use Supabase Pooler URL (IPv4 clean)
# ... imports

# Robust Engine Creation
def get_engine(url):
    return create_engine(
        url,
        connect_args={"check_same_thread": False} if "sqlite" in url else {},
        pool_pre_ping=True
    )

def get_db_path():
    """Returns safe DB path for both Dev and Frozen (Desktop) modes"""
    if getattr(sys, "frozen", False):
        # Running as PyInstaller exe -> %APPDATA%/k24
        # Default to user home if APPDATA missing
        base_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "k24")
        os.makedirs(base_dir, exist_ok=True)
        return os.path.join(base_dir, "k24_shadow.db")
    else:
        # Dev mode -> Force exact path to verify fix
        return r"C:\Users\Krisha Dewasi\OneDrive\Desktop\WEARE\weare\k24_shadow.db"

# Use absolute path to avoid CWD ambiguity
DEFAULT_DB = f"sqlite:///{get_db_path()}"

# Explicitly prefer Env Var but handle failure later
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB)

print(f"DEBUG: Initial DATABASE_URL: {DATABASE_URL}")

try:
    engine = get_engine(DATABASE_URL)
except Exception as e:
    print(f"❌ Failed to create engine with {DATABASE_URL}: {e}")
    engine = get_engine(DEFAULT_DB)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ... (rest of file) ...

def init_db():
    """Create tables with robust fallback"""
    global engine, SessionLocal
    try:
        print(f"🔄 Attempting DB Connection to: {engine.url}")
        Base.metadata.create_all(bind=engine)
        print("✅ DB Initialized Successfully.")
    except Exception as e:
        print(f"⚠️ DB Connection Failed: {e}")
        if "sqlite" not in str(engine.url):
            print("🔄 Switching to SQLite Fallback...")
            engine = get_engine(DEFAULT_DB)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            try:
                Base.metadata.create_all(bind=engine)
                print("✅ SQLite Fallback Initialized.")
            except Exception as ex:
                print(f"❌ SQLite Fallback Failed: {ex}")
                raise ex
        else:
            raise e



class TenantMixin:
    """Mixin to add tenant context to models"""
    tenant_id = Column(String, index=True, nullable=False, default="default")

class Ledger(TenantMixin, Base):
    """Mirrors a Tally Ledger"""
    __tablename__ = "ledgers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True) 
    alias = Column(String, nullable=True) # New
    parent = Column(String) # "under_group"
    ledger_type = Column(String, nullable=True, index=True) # customer, supplier, etc.
    
    # Financials
    opening_balance = Column(Float, default=0.0)
    closing_balance = Column(Float, default=0.0) # current_balance
    balance_type = Column(String, nullable=True) # Dr/Cr
    
    # Contact Details
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    pincode = Column(String, nullable=True)
    country = Column(String, default='India')
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    contact_person = Column(String, nullable=True)
    
    # Tax & compliance
    gstin = Column(String, index=True, nullable=True)
    pan = Column(String, nullable=True)
    gst_registration_type = Column(String, nullable=True)
    is_gst_applicable = Column(Boolean, default=False)
    
    # Credit Management
    credit_limit = Column(Float, nullable=True)
    credit_days = Column(Integer, nullable=True)
    
    # Metadata
    tally_guid = Column(String, index=True, nullable=True) 
    created_from = Column(String, default="Manual") # Tally, Web, Auto, Manual
    
    # Sync Status
    last_synced = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = Column(Boolean, default=True)

class Voucher(TenantMixin, Base):
    """Mirrors a Tally Voucher (Sales/Purchase)"""
    __tablename__ = "vouchers"

    # ── Enterprise-grade data integrity: duplicates physically impossible ──
    __table_args__ = (
        UniqueConstraint('tenant_id', 'guid', name='uq_voucher_tenant_guid'),
        Index('ix_voucher_is_deleted', 'is_deleted'),
    )

    id = Column(Integer, primary_key=True, index=True)
    guid = Column(String, index=True) # Removed unique constraint for multi-tenancy safe GUIDs
    voucher_number = Column(String)
    date = Column(DateTime)
    voucher_type = Column(String) # Sales, Purchase, Receipt, Payment
    party_name = Column(String) # Removed ForeignKey to decouple for now, or update logic later
    amount = Column(Float)
    narration = Column(String, nullable=True)

    # Sync Status
    sync_status = Column(String, default="SYNCED") # SYNCED, PENDING, ERROR
    last_synced = Column(DateTime, default=datetime.now)

    # Compliance & Workflow
    status = Column(String, default="Draft")  # Draft, Checked, Verified
    tds_section = Column(String, nullable=True)  # e.g., "194C", "194J"
    gst_reconciled = Column(Boolean, default=False)
    is_backdated = Column(Boolean, default=False)
    is_weekend_entry = Column(Boolean, default=False)

    # Phase D: Unified Action Engine
    source = Column(String, default='web')  # web, whatsapp, api
    tally_voucher_id = Column(String, nullable=True) # Stores Tally's VchID

    # Linked Ledger Reference
    ledger_id = Column(Integer, ForeignKey("ledgers.id"), nullable=True)

    # ── Line Items (populated during Tally sync, used by drawer/WhatsApp) ──
    # inventory_entries: [{name, quantity, rate, amount, godown}]
    # ledger_entries:    [{name, amount, is_tax}]
    inventory_entries = Column(JSON, nullable=True)
    ledger_entries = Column(JSON, nullable=True)

    # ── Soft Delete (Enterprise-grade: never lose audit trail) ──
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
    deleted_source = Column(String, nullable=True)  # "tally_sync", "user", "api"

class AuditLog(TenantMixin, Base):
    """Immutable Audit Trail for MCA Compliance"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String)  # "Voucher", "Ledger"
    entity_id = Column(String)    # GUID or ID
    user_id = Column(String)      # Who made the change
    action = Column(String)       # "CREATE", "UPDATE", "DELETE"
    timestamp = Column(DateTime, default=datetime.now)
    
    # The "What"
    old_value = Column(String, nullable=True)  # JSON dump
    new_value = Column(String, nullable=True)  # JSON dump
    
    # The "Why"
    reason = Column(String, nullable=False)

class StockItem(TenantMixin, Base):
    """Mirrors Tally Stock Item with comprehensive inventory fields"""
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    alias = Column(String, nullable=True)
    part_number = Column(String, nullable=True)
    description = Column(String, nullable=True) # New
    
    # Classification
    parent = Column(String, nullable=True) # Stock Group (keeping `parent` for compat, aliased conceptually)
    stock_group = Column(String, index=True, nullable=True) 
    stock_category = Column(String, nullable=True)
    item_type = Column(String, default='goods') # goods, services
    
    # Unit & Measurement
    units = Column(String, default="Nos") # Primary Unit
    alternate_unit = Column(String, nullable=True)
    conversion_factor = Column(Float, nullable=True)
    
    # Stock Tracking
    opening_stock = Column(Float, default=0.0)
    closing_balance = Column(Float, default=0.0) # current_stock
    minimum_stock = Column(Float, nullable=True)
    maximum_stock = Column(Float, nullable=True)
    reorder_quantity = Column(Float, nullable=True)
    
    # Pricing
    cost_price = Column(Float, default=0.0)
    selling_price = Column(Float, default=0.0)
    mrp = Column(Float, nullable=True)
    rate = Column(Float, default=0.0) # Last Known Rate
    valuation_method = Column(String, default='Average') # FIFO, LIFO, etc.
    
    # GST & Tax
    hsn_code = Column(String, index=True, nullable=True)
    gst_rate = Column(Float, default=0.0)
    taxability = Column(String, default='Taxable')
    cess_rate = Column(Float, default=0.0)
    
    # Multi-Location
    is_godown_tracking = Column(Boolean, default=False)
    default_godown = Column(String, nullable=True)
    
    # Metadata
    tally_guid = Column(String, index=True, nullable=True)
    created_from = Column(String, default='Manual')
    last_synced = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = Column(Boolean, default=True)

class StockMovement(TenantMixin, Base):
    """Tracks all stock transactions (InventoryEntry renamed/expanded)"""
    __tablename__ = "stock_movements"
                                        
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), index=True)
    voucher_id = Column(Integer, ForeignKey("vouchers.id"), nullable=True, index=True)
    
    movement_date = Column(DateTime, default=datetime.now, index=True)
    movement_type = Column(String) # IN, OUT, OPENING, ADJUSTMENT
    
    quantity = Column(Float, default=0.0)
    rate = Column(Float, default=0.0)
    amount = Column(Float, default=0.0)
    
    # Location
    godown_name = Column(String, nullable=True) # godown_from / to can be derived
    batch_name = Column(String, nullable=True)
    narration = Column(String, nullable=True)

# Alias InventoryEntry to StockMovement for backward compatibility during refactor
InventoryEntry = StockMovement

class Bill(TenantMixin, Base):
    """Mirrors Outstanding Bills (Receivables/Payables)"""
    __tablename__ = "bills"
    
    id = Column(Integer, primary_key=True, index=True)
    bill_name = Column(String, index=True) # Ref No
    party_name = Column(String) # Removed ForeignKey
    amount = Column(Float) # Positive = Receivable, Negative = Payable
    due_date = Column(DateTime, nullable=True)
    is_overdue = Column(Boolean, default=False)
    
    last_synced = Column(DateTime, default=datetime.now)


# Import Encryptor
from backend.database.encryption import encryptor

class Company(TenantMixin, Base):
    """Company/Organization details"""
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True) # Removed unique
    
    # Encrypted Backend Storage (Mapped to same DB columns)
    _gstin = Column("gstin", String, nullable=True)
    _pan = Column("pan", String, nullable=True)
    
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    pincode = Column(String, nullable=True)
    email = Column(String, nullable=True)
    
    _phone = Column("phone", String, nullable=True)
    
    # Tally Configuration
    tally_company_name = Column(String, nullable=True)
    tally_url = Column(String, default="http://localhost:9000")
    tally_edu_mode = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)

    # Hybrid Properties for Transparent Encryption
    @property
    def gstin(self):
        return encryptor.decrypt(self._gstin) if self._gstin else None
    
    @gstin.setter
    def gstin(self, value):
        self._gstin = encryptor.encrypt(value) if value else None

    @property
    def pan(self):
        return encryptor.decrypt(self._pan) if self._pan else None
    
    @pan.setter
    def pan(self, value):
        self._pan = encryptor.encrypt(value) if value else None

    @property
    def phone(self):
        return encryptor.decrypt(self._phone) if self._phone else None
    
    @phone.setter
    def phone(self, value):
        self._phone = encryptor.encrypt(value) if value else None


class User(TenantMixin, Base):
    """User accounts with role-based access"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True) 
    username = Column(String, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    
    # Role: admin, accountant, auditor, viewer
    role = Column(String, default="accountant")
    
    # Company association
    company_id = Column(Integer, ForeignKey("companies.id"))
    
    # API Keys
    google_api_key = Column(String, nullable=True)

    # WhatsApp Integration
    _whatsapp_number = Column("whatsapp_number", String, nullable=True)  
    
    whatsapp_verification_code = Column(String, nullable=True) # 6-digit OTP
    is_whatsapp_verified = Column(Boolean, default=False)
    whatsapp_linked_at = Column(DateTime, nullable=True)
    
    @property
    def whatsapp_number(self):
        return encryptor.decrypt(self._whatsapp_number) if self._whatsapp_number else None
    
    @whatsapp_number.setter
    def whatsapp_number(self, value):
        self._whatsapp_number = encryptor.encrypt(value) if value else None
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime, nullable=True)
    
    # Auto-execution settings
    auto_post_to_tally = Column(Boolean, default=False)  # If True, auto-post high-confidence vouchers

class UserSettings(TenantMixin, Base):
    """User preferences and settings"""
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # UI Preferences
    theme = Column(String, default="light")  # light, dark
    language = Column(String, default="en")
    
    # Notification Preferences
    email_notifications = Column(Boolean, default=True)
    tally_sync_alerts = Column(Boolean, default=True)
    
    # Feature Flags
    ai_chat_enabled = Column(Boolean, default=True)
    auto_backup = Column(Boolean, default=True)

    # Core Configuration (L0 Desktop Mode)
    tally_url = Column(String, default="http://localhost:9000")
    google_api_key = Column(String, nullable=True)
    
    # Auto-execution settings
    auto_post_to_tally = Column(Boolean, default=False)  # If True, auto-post high-confidence vouchers

class SyncState(TenantMixin, Base):
    """Tracks incremental sync progress"""
    __tablename__ = "sync_state"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String) # Removed unique constraint
    last_synced_at = Column(DateTime, default=datetime.now)
    last_checkpoint_val = Column(String, nullable=True) # e.g. last date "20240401"

class Tenant(Base):
    """
    Master table for Multi-Tenancy Identity.
    Maps String ID (TENANT-12345) to Business details & WhatsApp.
    """
    __tablename__ = "tenants"
    
    id = Column(String, primary_key=True, index=True) # e.g. "TENANT-12345"
    company_name = Column(String)
    tally_company_name = Column(String, nullable=True)
    whatsapp_number = Column(String, index=True, nullable=True) # Business WhatsApp Number
    license_key = Column(String, nullable=True)
    
    # Auto-execution settings
    auto_post_to_tally = Column(Boolean, default=False)  # If True, auto-post high-confidence vouchers
    
    created_at = Column(DateTime, default=datetime.now)

class WhatsAppMapping(TenantMixin, Base):
    """
    Maps External WhatsApp Users -> Internal Contacts
    """
    __tablename__ = "whatsapp_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    whatsapp_number = Column(String, index=True) # The sender's phone number
    contact_id = Column(Integer, ForeignKey("ledgers.id"), nullable=True) # Linked Ledger/Contact
    
    created_at = Column(DateTime, default=datetime.now)

class OnboardingState(Base):
    """
    Tracks user onboarding progress for WhatsApp
    """
    __tablename__ = "onboarding_states"

    phone = Column(String, primary_key=True, index=True)
    current_step = Column(String, default="new")
    temp_data = Column(JSON, default=dict)
    otp = Column(String, nullable=True)
    otp_expiry = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


def init_db():
    """Create tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ChatHistory(TenantMixin, Base):
    """Persist all chat interactions for audit and analytics."""
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    user_phone = Column(String, index=True, nullable=False)
    message_content = Column(String, nullable=True)
    ai_response = Column(String, nullable=True)
    has_image = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.now)

class GSTLedger(TenantMixin, Base):
    """Maps configured GST tax ledgers locally"""
    __tablename__ = "gst_ledgers"
    
    id = Column(Integer, primary_key=True, index=True)
    rate = Column(Float) # 5.0, 12.0 ...
    tax_type = Column(String) # CGST, SGST, IGST
    ledger_name = Column(String) # "CGST @ 9%"
    tally_guid = Column(String, nullable=True) # Remote ID
    
    last_synced = Column(DateTime, default=datetime.now)

class DeviceLicense(TenantMixin, Base):
    """Tracks authorized desktop devices for licensing"""
    __tablename__ = "device_licenses"
    
    id = Column(Integer, primary_key=True, index=True)
    license_key = Column(String, unique=True, index=True)
    user_id = Column(String, index=True)
    device_fingerprint = Column(String, index=True)
    status = Column(String, default="active") # active, revoked
    
    app_version = Column(String, nullable=True)
    first_activated_at = Column(DateTime, default=datetime.now)
    last_validated_at = Column(DateTime, default=datetime.now)
    last_heartbeat = Column(DateTime, default=datetime.now)
    
    created_at = Column(DateTime, default=datetime.now)
