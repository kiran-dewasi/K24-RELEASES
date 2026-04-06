# ============================================================
# TENANT_CONFIG TABLE — Supabase (k24-main) — PHASE 1 STATE
# Updated: 2026-04-05
# Migration: phase1_tenant_config_additive_columns
#
# COLUMNS:
#   tenant_id              TEXT  NOT NULL  PK
#   whatsapp_number        TEXT  NOT NULL
#   user_email             TEXT  NOT NULL
#   company_name           TEXT  nullable
#   subscription_status    TEXT  nullable  default='trial'
#   trial_ends_at          TIMESTAMPTZ nullable
#   subscription_ends_at   TIMESTAMPTZ nullable
#   created_at             TIMESTAMPTZ default=now()
#   updated_at             TIMESTAMPTZ default=now()  (auto-updated by trigger)
#   owner_name             TEXT  nullable              -- NEW Phase 1
#   tally_company_name     TEXT  nullable              -- NEW Phase 1
#   trial_start_at         TIMESTAMPTZ nullable        -- NEW Phase 1
#   trial_credit_limit     INTEGER     default=90      -- NEW Phase 1
#   trial_credits_used     INTEGER     default=0       -- NEW Phase 1
#   onboarding_source      TEXT        default='web'   -- NEW Phase 1 ('web' or 'whatsapp')
#   razorpay_customer_id   TEXT  nullable              -- NEW Phase 1 (for Phase 3 Razorpay)
#
# RULES:
# - tenant_config is the SINGLE SOURCE OF TRUTH for subscription + trial state
# - Do NOT use subscriptions table as a gatekeeper; it is a secondary/reporting table
# - Every tenant creation (web OR WhatsApp) must write to tenant_config
# - onboarding_source must always be set ('web' or 'whatsapp')
# - trial_start_at + trial_ends_at MUST both be set on tenant creation
# ============================================================

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class TenantMixin:
    """Mixin for tables that carry a tenant_id column."""
    tenant_id = Column(String, index=True, nullable=True)


# ---------------------------------------------------------------------------
# Company – transitional stub; prefer users_profile.company_name for cloud
# ---------------------------------------------------------------------------
class Company(Base):
    __tablename__ = "companies"

    id             = Column(String, primary_key=True, index=True)
    name           = Column(String, index=True, nullable=True)
    tenant_id      = Column(String, index=True, nullable=True)
    address        = Column(String, nullable=True)
    city           = Column(String, nullable=True)
    state          = Column(String, nullable=True)
    pincode        = Column(String, nullable=True)
    email          = Column(String, nullable=True)
    gstin          = Column(String, nullable=True)
    pan            = Column(String, nullable=True)
    phone          = Column(String, nullable=True)
    tally_company_name = Column(String, nullable=True)
    tally_url      = Column(String, default="http://localhost:9000")
    tally_edu_mode = Column(Boolean, default=False)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    is_active      = Column(Boolean, default=True)


# ---------------------------------------------------------------------------
# User — maps EXACTLY to public.users_profile
# PK = Supabase auth.users UUID; no password/username stored here
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users_profile"

    id               = Column(String, primary_key=True, index=True)   # UUID from auth.users
    full_name        = Column(Text, nullable=False)
    whatsapp_number  = Column(Text, nullable=True)
    avatar_url       = Column(Text, nullable=True)
    role             = Column(Text, default="owner")
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    tenant_id        = Column(String, index=True, nullable=True)
    company_name     = Column(Text, nullable=True)
    is_active        = Column(Boolean, default=True)
    language         = Column(String, default="en")
    updated_at       = Column(DateTime(timezone=True), nullable=True)
    last_login_at    = Column(DateTime(timezone=True), nullable=True)
    is_verified      = Column(Boolean, default=False)


# ---------------------------------------------------------------------------
# UserSettings — maps to public.user_settings (cloud-safe columns only)
# Local-only columns (tally_sync_alerts, auto_backup, tally_url,
# google_api_key, auto_post_to_tally) are intentionally absent.
# ---------------------------------------------------------------------------
class UserSettings(Base):
    __tablename__ = "user_settings"

    id                  = Column(Integer, primary_key=True)
    user_id             = Column(Integer, nullable=True)   # TODO: migrate to UUID FK → users_profile.id
    theme               = Column(String, nullable=True)
    language            = Column(String, nullable=True)
    email_notifications = Column(Boolean, nullable=True)
    ai_chat_enabled     = Column(Boolean, nullable=True)
    tenant_id           = Column(String, nullable=False)
