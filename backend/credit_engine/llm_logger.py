"""
Credit Engine â€” LLM Call Logger
================================
Lightweight fire-and-forget logging of LLM API calls.
Used ONLY for cost analytics and model tuning â€” NOT for billing.

Call log_llm_call() anywhere you invoke an LLM API, passing the token counts
and a workflow name so you can analyse cost per workflow type.

Example usage in agent_gemini.py:
    from credit_engine import log_llm_call

    response = model.generate_content(prompt)
    log_llm_call(
        tenant_id     = tenant_id,
        model         = "gemini-2.0-flash",
        workflow      = "bill_extraction",
        tokens_input  = response.usage_metadata.prompt_token_count,
        tokens_output = response.usage_metadata.candidates_token_count,
        usage_event_id = decision.event_id,   # link to the usage event if available
    )
"""

import logging
import asyncio
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from database.supabase_client import supabase

logger = logging.getLogger(__name__)

# Thread pool for fire-and-forget logging (non-blocking to callers)
_log_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="llm_logger")

# Cost per 1M tokens in USD (update as pricing changes)
# These are approximate for budget estimation only
_COST_PER_MILLION_INPUT: dict  = {
    "gemini-2.0-flash":         0.075,
    "gemini-1.5-pro":           1.25,
    "gemini-1.5-flash":         0.075,
    "deepseek-chat":            0.27,
    "deepseek-reasoner":        0.55,
    "default":                  0.50,
}
_COST_PER_MILLION_OUTPUT: dict = {
    "gemini-2.0-flash":         0.30,
    "gemini-1.5-pro":           5.00,
    "gemini-1.5-flash":         0.30,
    "deepseek-chat":            1.10,
    "deepseek-reasoner":        2.19,
    "default":                  1.50,
}


def _estimate_cost_usd(model: str, tokens_input: int, tokens_output: int) -> float:
    """Estimate the USD cost of an LLM call based on token counts."""
    cost_in  = _COST_PER_MILLION_INPUT.get(model,  _COST_PER_MILLION_INPUT["default"])
    cost_out = _COST_PER_MILLION_OUTPUT.get(model, _COST_PER_MILLION_OUTPUT["default"])
    return (tokens_input / 1_000_000 * cost_in) + (tokens_output / 1_000_000 * cost_out)


def _write_llm_call_to_db(
    tenant_id:       str,
    model:           str,
    workflow:        Optional[str],
    tokens_input:    int,
    tokens_output:   int,
    cost_usd:        float,
    duration_ms:     Optional[int],
    usage_event_id:  Optional[str],
) -> None:
    """Synchronous DB write â€” runs in the thread pool."""
    try:
        supabase.table("llm_calls").insert({
            "tenant_id":         tenant_id,
            "usage_event_id":    usage_event_id,
            "model":             model,
            "workflow":          workflow,
            "tokens_input":      tokens_input,
            "tokens_output":     tokens_output,
            "cost_estimated_usd": cost_usd,
            "duration_ms":       duration_ms,
        }).execute()
    except Exception as exc:
        logger.warning(f"[LLMLogger] Failed to write llm_call to DB: {exc}")


def log_llm_call(
    tenant_id:      str,
    model:          str,
    tokens_input:   int,
    tokens_output:  int,
    workflow:       Optional[str]  = None,
    duration_ms:    Optional[int]  = None,
    usage_event_id: Optional[str]  = None,
    cost_usd:       Optional[float] = None,
) -> None:
    """
    Log an LLM API call for cost analytics. Non-blocking.

    This function is fire-and-forget â€” it submits the DB write to a
    background thread and returns immediately. Callers are never blocked.

    Args:
        tenant_id:      Tenant string ID.
        model:          Model name (e.g. 'gemini-2.0-flash', 'deepseek-chat').
        tokens_input:   Input/prompt token count.
        tokens_output:  Output/completion token count.
        workflow:       Descriptive workflow name for analytics grouping.
                        e.g. 'bill_extraction', 'voucher_creation', 'kittu_query',
                             'ledger_lookup', 'gst_query'
        duration_ms:    Time taken for the LLM call in milliseconds.
        usage_event_id: Optional UUID linking to a usage_events row.
        cost_usd:       Override estimated cost (if you have exact billing data).
    """
    if not tenant_id:
        return  # Skip logging for system/unattributed calls

    estimated_cost = cost_usd if cost_usd is not None else _estimate_cost_usd(
        model, tokens_input, tokens_output
    )

    # Submit to background thread â€” never blocks the request path
    _log_executor.submit(
        _write_llm_call_to_db,
        tenant_id,
        model,
        workflow,
        tokens_input,
        tokens_output,
        estimated_cost,
        duration_ms,
        usage_event_id,
    )

    logger.debug(
        f"[LLMLogger] Queued log: tenant={tenant_id} model={model} "
        f"in={tokens_input} out={tokens_output} workflow={workflow} "
        f"cost=${estimated_cost:.6f}"
    )

