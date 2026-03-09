"""
K24 Credit Engine
=================
The single source of truth for all usage tracking and credit accounting.

All business flows (WhatsApp, Kittu, Tally sync) MUST call record_event()
from here. No code outside this package should write directly to usage tables.

Public API:
    record_event(...)   → CreditDecision   # Track an event and apply credits
    log_llm_call(...)   → None             # Log an LLM API call for cost analytics
"""

from backend.credit_engine.engine import record_event, get_tenant_usage
from backend.credit_engine.llm_logger import log_llm_call
from backend.credit_engine.models import (
    CreditDecision,
    CreditStatus,
    EventType,
    EventSubtype,
)

__all__ = [
    "record_event",
    "get_tenant_usage",
    "log_llm_call",
    "CreditDecision",
    "CreditStatus",
    "EventType",
    "EventSubtype",
]
