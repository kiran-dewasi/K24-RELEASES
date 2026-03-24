"""
Credit Engine â€” Rating Module
==============================
Computes how many credits a given event should consume by looking up
the active rule in the `credit_rules` table.

All credit math lives here. If you need to change a credit cost,
update the DB row in `credit_rules` â€” not this file.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from database.supabase_client import supabase  # noqa: E402
from credit_engine.models import EventType, EventSubtype

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-process rule cache: keyed by (event_type, event_subtype).
# Refreshed automatically when stale (TTL = 5 minutes).
# This avoids a DB round-trip on every single WhatsApp message.
# ---------------------------------------------------------------------------
_RULE_CACHE: Dict[str, float]       = {}
_CACHE_LOADED_AT: Optional[datetime] = None
_CACHE_TTL_SECONDS: int              = 300   # 5 minutes


def _is_cache_stale() -> bool:
    """Returns True if the rule cache needs a refresh."""
    if _CACHE_LOADED_AT is None:
        return True
    age = (datetime.now(timezone.utc) - _CACHE_LOADED_AT).total_seconds()
    return age > _CACHE_TTL_SECONDS


def _cache_key(event_type: str, event_subtype: str) -> str:
    return f"{event_type}::{event_subtype}"


def _load_rules_into_cache() -> None:
    """
    Fetch all active, currently-effective credit rules from Supabase
    and populate the in-process cache.
    """
    global _RULE_CACHE, _CACHE_LOADED_AT

    try:
        result = (
            supabase.table("credit_rules")
            .select("event_type,event_subtype,credits")
            .eq("is_active", True)
            .execute()
        )

        rows = result.data or []
        now_str = datetime.now(timezone.utc).isoformat()

        new_cache: Dict[str, float] = {}
        for row in rows:
            # Skip rules that haven't started yet or have expired
            eff_from = row.get("effective_from") or ""
            eff_to   = row.get("effective_to")

            if eff_from and eff_from > now_str:
                continue   # Not yet active

            if eff_to and eff_to < now_str:
                continue   # Already expired

            key              = _cache_key(row["event_type"], row["event_subtype"])
            new_cache[key]   = float(row["credits"])

        _RULE_CACHE       = new_cache
        _CACHE_LOADED_AT  = datetime.now(timezone.utc)

        logger.info(f"[CreditRating] Loaded {len(_RULE_CACHE)} active rules into cache.")

    except Exception as exc:
        logger.error(f"[CreditRating] Failed to load credit rules: {exc}")
        # Keep stale cache rather than crashing â€” fail open with 0 credits
        if _CACHE_LOADED_AT is None:
            _RULE_CACHE = {}


def compute_credits(
    event_type:    str,
    event_subtype: str,
    metadata:      Optional[Dict[str, Any]] = None,
) -> float:
    """
    Look up the configured credit cost for this event type + subtype.

    Args:
        event_type:    One of VOUCHER, DOCUMENT, MESSAGE.
        event_subtype: Fine-grained subtype (created, updated, page_processed, etc.)
        metadata:      Optional context (reserved for future conditional rules).

    Returns:
        Number of credits to consume (0.0 if no rule found â†’ free by default).

    Notes:
        - Results are cached for _CACHE_TTL_SECONDS to avoid per-event DB hits.
        - If Supabase is unavailable, uses stale cache or defaults to 0.
    """
    if _is_cache_stale():
        _load_rules_into_cache()

    key     = _cache_key(event_type, event_subtype)
    credits = _RULE_CACHE.get(key, 0.0)

    # â”€â”€ Future hook: apply condition-based multipliers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Example: multi-page documents could cost page_count * base_rate
    #   if event_type == "DOCUMENT" and metadata and "page_count" in metadata:
    #       multiplier = metadata["page_count"]
    #       credits *= multiplier
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    logger.debug(f"[CreditRating] {event_type}/{event_subtype} â†’ {credits} credits")
    return credits


def invalidate_rule_cache() -> None:
    """
    Force-clear the rule cache so the next call reloads from DB.
    Call this from the admin API after updating a credit rule.
    """
    global _CACHE_LOADED_AT
    _CACHE_LOADED_AT = None
    logger.info("[CreditRating] Rule cache invalidated.")

