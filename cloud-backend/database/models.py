from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class TenantMixin:
    tenant_id = Column(String, index=True, nullable=False, default="default")

class Company(TenantMixin, Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    pincode = Column(String, nullable=True)
    email = Column(String, nullable=True)
    gstin = Column(String, nullable=True)
    pan = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    tally_company_name = Column(String, nullable=True)
    tally_url = Column(String, default="http://localhost:9000")
    tally_edu_mode = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)

class User(TenantMixin, Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    username = Column(String, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    role = Column(String, default="accountant")
    company_id = Column(Integer, ForeignKey("companies.id"))
    google_api_key = Column(String, nullable=True)
    whatsapp_number = Column(String, nullable=True)
    whatsapp_verification_code = Column(String, nullable=True)
    is_whatsapp_verified = Column(Boolean, default=False)
    whatsapp_linked_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime, nullable=True)

class UserSettings(TenantMixin, Base):
    __tablename__ = "user_settings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    theme = Column(String, default="light")
    language = Column(String, default="en")
    email_notifications = Column(Boolean, default=True)
    tally_sync_alerts = Column(Boolean, default=True)
    ai_chat_enabled = Column(Boolean, default=True)
    auto_backup = Column(Boolean, default=True)
    tally_url = Column(String, default="http://localhost:9000")
    google_api_key = Column(String, nullable=True)
