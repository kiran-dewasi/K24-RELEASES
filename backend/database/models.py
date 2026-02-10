from datetime import datetime
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, EmailStr
import uuid

class ChatMessage(BaseModel):
    """Single chat message"""
    thread_id: str
    role: str  # 'user' or 'assistant'
    content: str
    source: str = 'ui'  # 'ui' or 'whatsapp'
    user_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "thread_id": "550e8400-e29b-41d4-a716-446655440000",
                "role": "user",
                "content": "Create customer Sharma & Sons",
                "source": "ui",
                "user_id": "user@k24.ai"
            }
        }

class AuditLogEntry(BaseModel):
    """Immutable audit log entry"""
    table_name: str
    record_id: str
    operation: str  # 'CREATE', 'UPDATE', 'DELETE'
    executed_by: str
    triggered_by_message_id: Optional[str] = None
    thread_id: Optional[str] = None
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    celery_task_id: Optional[str] = None
    financial_impact: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}

class TaskProgress(BaseModel):
    """Track task execution progress"""
    celery_task_id: str
    thread_id: str
    operation: str
    status: str = 'pending'
    current_step: Optional[str] = None
    progress_percent: int = 0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# ============================================
# PHASE 1: HYBRID DATABASE MODELS (SUPABASE)
# ============================================

class UserProfile(BaseModel):
    """Corresponds to user_profiles table"""
    id: uuid.UUID
    tenant_id: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Subscription(BaseModel):
    """Corresponds to subscriptions table"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    tenant_id: str
    plan: Literal['free', 'pro', 'enterprise'] = 'free'
    status: Literal['active', 'trial', 'expired', 'cancelled'] = 'trial'
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    device_limit: int = 1
    features_json: Dict[str, Any] = {}
    payment_provider: Optional[str] = None
    payment_subscription_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class DeviceLicense(BaseModel):
    """Corresponds to device_licenses table"""
    license_key: str
    user_id: uuid.UUID
    tenant_id: str
    device_fingerprint: str
    device_name: Optional[str] = None
    os_version: Optional[str] = None
    app_version: Optional[str] = None
    status: Literal['active', 'suspended', 'revoked'] = 'active'
    activated_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    grace_period_until: Optional[datetime] = None
    created_at: Optional[datetime] = None

class WhatsappBinding(BaseModel):
    """Corresponds to whatsapp_bindings table"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    tenant_id: str
    whatsapp_number: str
    verified: bool = False
    verification_code: Optional[str] = None
    code_expires_at: Optional[datetime] = None
    connected_at: Optional[datetime] = None
    session_status: Literal['pending', 'connected', 'disconnected', 'expired'] = 'pending'
    last_message_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class WhatsappCustomerMapping(BaseModel):
    """Corresponds to whatsapp_customer_mappings table"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    tenant_id: str
    customer_phone: str
    customer_name: str
    client_code: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class SyncCheckpoint(BaseModel):
    """Corresponds to sync_checkpoints table"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    tenant_id: str
    device_fingerprint: Optional[str] = None
    backup_size_bytes: Optional[int] = None
    backup_url: Optional[str] = None
    encryption_key_hash: Optional[str] = None
    status: Literal['pending', 'completed', 'failed'] = 'pending'
    created_at: Optional[datetime] = None
