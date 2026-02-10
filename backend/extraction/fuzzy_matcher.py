"""
K24 Parameter Extraction - Fuzzy Matching
==========================================
Fuzzy matching for ledger names with min ratio 0.80.
"""

import difflib
from typing import List, Tuple, Optional
import logging
from backend.database import SessionLocal, Ledger

logger = logging.getLogger(__name__)

MIN_FUZZY_RATIO = 0.80
MAX_SUGGESTIONS = 3

def fuzzy_match_ledger(
    customer_name: str,
    min_ratio: float = MIN_FUZZY_RATIO,
    max_results: int = MAX_SUGGESTIONS
) -> List[Tuple[str, float]]:
    """
    Fuzzy match customer name against Tally ledger master.
    
    Args:
        customer_name: Input customer name
        min_ratio: Minimum similarity ratio (default 0.80)
        max_results: Maximum number of suggestions (default 3)
        
    Returns:
        List of (ledger_name, confidence) tuples sorted by confidence
        
    Example:
        >>> fuzzy_match_ledger("HDFC")
        [("HDFC Bank A/c 123", 0.85), ("HDFC Credit Card", 0.82)]
    """
    db = SessionLocal()
    try:
        # Get all ledger names from database
        ledgers = db.query(Ledger.name).filter(Ledger.is_active == True).all()
        ledger_names = [ledger[0] for ledger in ledgers]
        
        if not ledger_names:
            logger.warning("No ledgers found in database")
            return []
        
        # Use difflib for fuzzy matching
        matches = difflib.get_close_matches(
            customer_name,
            ledger_names,
            n=max_results,
            cutoff=min_ratio
        )
        
        # Calculate confidence scores
        results = []
        for match in matches:
            # Use SequenceMatcher for exact ratio
            ratio = difflib.SequenceMatcher(None, customer_name.lower(), match.lower()).ratio()
            results.append((match, round(ratio, 2)))
        
        # Sort by confidence (highest first)
        results.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"Fuzzy matched '{customer_name}' -> {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"Fuzzy matching error: {e}")
        return []
    finally:
        db.close()

def exact_match_ledger(customer_name: str) -> Optional[str]:
    """
    Try exact match first (case-insensitive).
    
    Args:
        customer_name: Input customer name
        
    Returns:
        Ledger name if exact match found, None otherwise
    """
    db = SessionLocal()
    try:
        ledger = db.query(Ledger).filter(
            Ledger.name.ilike(customer_name),
            Ledger.is_active == True
        ).first()
        
        if ledger:
            logger.info(f"Exact match found: {ledger.name}")
            return ledger.name
        
        return None
        
    except Exception as e:
        logger.error(f"Exact match error: {e}")
        return None
    finally:
        db.close()

def match_ledger_with_fallback(customer_name: str) -> Tuple[Optional[str], float, List[str]]:
    """
    Try exact match first, then fuzzy match.
    
    Args:
        customer_name: Input customer name
        
    Returns:
        Tuple of (matched_name, confidence, alternatives)
        
    Example:
        >>> match_ledger_with_fallback("HDFC")
        ("HDFC Bank A/c 123", 1.0, [])
        
        >>> match_ledger_with_fallback("ABC")
        (None, 0.0, ["ABC Corp", "ABC Ltd", "ABC Industries"])
    """
    # Try exact match first
    exact = exact_match_ledger(customer_name)
    if exact:
        return (exact, 1.0, [])
    
    # Try fuzzy match
    fuzzy_results = fuzzy_match_ledger(customer_name)
    
    if not fuzzy_results:
        return (None, 0.0, [])
    
    # If top match has high confidence, use it
    top_match, top_confidence = fuzzy_results[0]
    
    if top_confidence >= 0.90:
        # Very high confidence, use it
        return (top_match, top_confidence, [])
    else:
        # Lower confidence, provide alternatives
        alternatives = [name for name, _ in fuzzy_results]
        return (None, top_confidence, alternatives)

def get_ledger_details(ledger_name: str) -> Optional[dict]:
    """
    Get ledger details from database.
    
    Args:
        ledger_name: Ledger name
        
    Returns:
        Dictionary with ledger details or None
    """
    db = SessionLocal()
    try:
        ledger = db.query(Ledger).filter(
            Ledger.name == ledger_name,
            Ledger.is_active == True
        ).first()
        
        if ledger:
            return {
                "id": ledger.id,
                "name": ledger.name,
                "parent": ledger.parent,
                "opening_balance": ledger.opening_balance,
                "closing_balance": ledger.closing_balance,
                "gstin": ledger.gstin,
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Get ledger details error: {e}")
        return None
    finally:
        db.close()
