"""
Fallback entity extractor for when LLM quota is exceeded.
Uses regex patterns to extract party names and amounts from natural language.
"""
import re
from typing import Optional, Dict, Any


def extract_entity_fallback(message: str, intent_action: str) -> Optional[str]:
    """
    Extract entity (party name) from message using regex patterns.
    
    Args:
        message: User's natural language message
        intent_action: The recognized intent (create_sale, create_purchase, etc.)
        
    Returns:
        Extracted entity name or None
    """
    message_lower = message.lower()
    
    # Patterns for sales
    if intent_action == "create_sale":
        patterns = [
            r'sold.*to\s+([a-z0-9\s&]+?)(?:\s+\(|,|\.|$)',
            r'sales?\s+to\s+([a-z0-9\s&]+?)(?:\s+\(|,|\.|$)',
            r'customer\s+([a-z0-9\s&]+?)(?:\s+\(|,|\.|$)',
        ]
    # Patterns for purchases
    elif intent_action == "create_purchase":
        patterns = [
            r'bought.*from\s+([a-z0-9\s&]+?)(?:\s+\(|,|\.|$)',
            r'purchase.*from\s+([a-z0-9\s&]+?)(?:\s+\(|,|\.|$)',
            r'supplier\s+([a-z0-9\s&]+?)(?:\s+\(|,|\.|$)',
        ]
    # Patterns for GSTIN updates
    elif intent_action == "update_gstin":
        patterns = [
            r'gstin.*for\s+([a-z0-9\s&]+?)(?:\s+to\s+|\s+\(|,|\.|$)',
            r'update\s+([a-z0-9\s&]+?)(?:\'s)?\s+gstin',
            r'party\s+([a-z0-9\s&]+?)(?:\s+to\s+|\s+\(|,|\.|$)',
        ]
    else:
        return None
    
    for pattern in patterns:
        match = re.search(pattern, message_lower)
        if match:
            entity = match.group(1).strip()
            # Capitalize each word
            return ' '.join(word.capitalize() for word in entity.split())
    
    return None


def extract_parameters_fallback(message: str) -> Dict[str, Any]:
    """
    Extract parameters (quantity, amount, rate, item, gstin) using regex.
    
    Args:
        message: User's natural language message
        
    Returns:
        Dictionary with extracted parameters
    """
    params = {}
    message_lower = message.lower()
    
    # Extract GSTIN (Standard format: 22AAAAA0000A1Z5)
    # We use a slightly looser regex for extraction to catch potential user inputs
    gstin_pattern = r'\b\d{2}[a-z]{5}\d{4}[a-z]{1}[1-9a-z]{1}z[0-9a-z]{1}\b'
    match = re.search(gstin_pattern, message_lower)
    if match:
        params['gstin'] = match.group(0).upper()

    # Extract quantity
    qty_patterns = [
        r'(\d+)\s*(?:bags?|units?|items?|pieces?)',
        r'(?:quantity|qty)[:\s]+(\d+)',
    ]
    for pattern in qty_patterns:
        match = re.search(pattern, message_lower)
        if match:
            params['quantity'] = int(match.group(1))
            break
    
    # Extract rate (price per unit)
    rate_patterns = [
        r'(?:@|price|rate|avg\.?\s*price)[:\s]*(?:inr|rs\.?|₹)?\s*(\d+)',
        r'(?:inr|rs\.?|₹)\s*(\d+)\s*(?:per|each|/@)',
    ]
    for pattern in rate_patterns:
        match = re.search(pattern, message_lower)
        if match:
            params['rate'] = float(match.group(1))
            break
    
    # Extract total amount
    amt_patterns = [
        r'(?:total|amount)[:\s]*(?:inr|rs\.?|₹)?\s*(\d+)',
        r'(?:for|of)\s*(?:inr|rs\.?|₹)\s*(\d+)(?:\s|$)',
    ]
    for pattern in amt_patterns:
        match = re.search(pattern, message_lower)
        if match:
            params['amount'] = float(match.group(1))
            break
    
    # Extract item name (simplified - just look for common patterns)
    item_patterns = [
        r'(?:bags? of|sold|bought)\s+([a-z]+)',
    ]
    for pattern in item_patterns:
        match = re.search(pattern, message_lower)
        if match:
            params['item'] = match.group(1)
            break
    
    # Extract unit weight
    weight_pattern = r'(\d+)\s*kg'
    match = re.search(weight_pattern, message_lower)
    if match:
        params['unit_weight'] = f"{match.group(1)} kg"
    
    return params
