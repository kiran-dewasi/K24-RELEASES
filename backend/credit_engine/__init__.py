"""
K24 Credit Engine
=================
The single source of truth for all usage tracking and credit accounting.

All business flows (WhatsApp, Kittu, Tally sync) MUST call record_event()
from here. No code outside this package should write directly to usage tables.

Public API:
    record_event(...)   â†’ CreditDecision   # Track an event and apply credits
    log_llm_call(...)   â†’ None             # Log an LLM API call for cost analytics
"""

from credit_engine.engine import record_event, get_tenant_usage
from credit_engine.llm_logger import log_llm_call
from credit_engine.models import (
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

