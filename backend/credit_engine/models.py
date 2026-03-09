"""
Credit Engine — Pydantic Models & Enums
========================================
All shared data structures for the credit system.
Keep these clean: they are passed across module boundaries.
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class EventType(str, Enum):
    """Top-level category of a business event."""
    VOUCHER  = "VOUCHER"    # Created/updated in Tally
    DOCUMENT = "DOCUMENT"   # Image/PDF page processed
    MESSAGE  = "MESSAGE"    # WhatsApp / Kittu message


class EventSubtype(str, Enum):
    """Fine-grained subtype used to look up the credit rule."""
    # VOUCHER subtypes
    VOUCHER_CREATED  = "created"
    VOUCHER_UPDATED  = "updated"

    # DOCUMENT subtypes
    PAGE_PROCESSED   = "page_processed"

    # MESSAGE subtypes
    ACTION           = "action"       # Message triggered real work
    INFO_QUERY       = "info_query"   # Purely informational question


class CreditStatus(str, Enum):
    """
    The decision returned by the credit engine after processing an event.
    Callers should check this and act accordingly.

    ALLOWED      — within limit, proceed normally.
    NEAR_LIMIT   — within 20% of plan limit (warn user, suggest upgrade).
    OVER_LIMIT   — exceeded limit but plan is SOFT_CAP (allow, flag for upgrade nudge).
    BLOCKED      — exceeded limit and plan is HARD_CAP (reject the action).
    """
    ALLOWED    = "ALLOWED"
    NEAR_LIMIT = "NEAR_LIMIT"
    OVER_LIMIT = "OVER_LIMIT"
    BLOCKED    = "BLOCKED"


class UsageEventIn(BaseModel):
    """
    Input payload for record_event().
    Callers provide this; the engine handles the rest.
    """
    tenant_id:    str
    company_id:   Optional[int]           = None
    event_type:   EventType
    event_subtype: EventSubtype
    source:       str                     = "api"   # whatsapp | kittu | api | web | tally_sync
    metadata:     Dict[str, Any]          = Field(default_factory=dict)


class UsageSummary(BaseModel):
    """Snapshot of a tenant's usage for the current billing cycle."""
    tenant_id:             str
    billing_cycle_id:      Optional[str]   = None
    cycle_start:           Optional[datetime] = None
    cycle_end:             Optional[datetime] = None
    max_credits:           int             = 0
    credits_used_total:    float           = 0.0
    credits_used_voucher:  float           = 0.0
    credits_used_document: float           = 0.0
    credits_used_message:  float           = 0.0
    events_count_total:    int             = 0
    percent_used:          float           = 0.0
    plan_id:               Optional[str]   = None
    enforcement_mode:      str             = "HARD_CAP"


class CreditDecision(BaseModel):
    """
    The complete response from record_event().
    Callers use .status to decide whether to proceed or block.
    """
    event_id:         str               # UUID of the usage_event row created
    tenant_id:        str
    credits_consumed: float             # How many credits this event cost
    status:           CreditStatus      # ALLOWED | NEAR_LIMIT | OVER_LIMIT | BLOCKED
    usage:            UsageSummary      # Full updated usage snapshot
    message:          str = ""         # Human-readable note (for logs / upgrade prompts)

    @property
    def is_blocked(self) -> bool:
        return self.status == CreditStatus.BLOCKED

    @property
    def should_warn(self) -> bool:
        return self.status in (CreditStatus.NEAR_LIMIT, CreditStatus.OVER_LIMIT)
