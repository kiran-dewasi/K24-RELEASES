from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class TenantMixin:
    """Mixin for tables that carry a tenant_id column."""
    tenant_id = Column(String, index=True, nullable=True)


# ---------------------------------------------------------------------------
# Company – still referenced by cloud auth router (company stub creation)
# ---------------------------------------------------------------------------
class Company(Base):
    """
    Local/cloud company stub.
    Used transitionally; prefer Supabase user_profiles.company_name for cloud.
    """
    __tablename__ = "companies"

    id = Column(String, primary_key=True, index=True)   # UUID stored as text
    name = Column(String, index=True, nullable=True)
    tenant_id = Column(String, index=True, nullable=True)
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
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)


# ---------------------------------------------------------------------------
# User – maps to Supabase public.user_profiles
# ---------------------------------------------------------------------------
class User(Base):
    """
    Profile extension of Supabase Auth.
    Maps to: public.user_profiles (production schema).

    The primary key `id` is the UUID issued by Supabase Auth (auth.users.id).
    No email / username / hashed_password here — authentication is handled
    entirely by Supabase Auth; this model only stores profile data.
    """
    __tablename__ = "user_profiles"

    # PK = Supabase auth.users UUID
    id = Column(String, primary_key=True, index=True)   # UUID as text / String

    # ------------------------------------------------------------------
    # Core profile fields (match SUPABASE_PRODUCTION_SCHEMA.md)
    # ------------------------------------------------------------------
    tenant_id = Column(String, unique=True, index=True, nullable=True)
    full_name = Column(Text, nullable=True)
    role = Column(String, nullable=True, default="owner")        # kept for app logic
    language = Column(String, nullable=True, default="en")
    is_active = Column(Boolean, default=True)

    # Optional: present in V1 schema (supabase_schema.sql)
    whatsapp_number = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)   # stored as last_login_at in Supabase

    # ------------------------------------------------------------------
    # Convenience alias so existing call-sites using `user.last_login`
    # continue to work without a migration step.
    # ------------------------------------------------------------------
    @property
    def last_login(self):
        return self.last_login_at

    @last_login.setter
    def last_login(self, value):
        self.last_login_at = value
