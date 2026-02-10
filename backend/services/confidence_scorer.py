"""
Confidence Scoring System for Bill Data Extraction
===================================================
Calculates confidence score to determine if auto-execution is warranted.
If confidence >= 95%, auto-create + post to Tally without asking questions.
"""

from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


def calculate_overall_confidence(bill_data: Dict) -> float:
    """
    Calculate confidence score for auto-execution decision.
    
    Factors considered:
    1. AI's self-reported confidence
    2. Required fields completeness
    3. Items completeness (name, quantity, rate, amount, unit)
    4. Math validation (amounts add up correctly)
    5. GST calculation validity (within reasonable range)
    
    Returns: 0.0 to 1.0 (multiply by 100 for percentage)
    """
    
    scores = []
    weights = []
    
    # Factor 1: AI's self-reported confidence (weight: 2)
    if 'confidence' in bill_data and bill_data['confidence'] is not None:
        ai_confidence = float(bill_data['confidence'])
        # Normalize if it's a percentage (e.g., 95 -> 0.95)
        if ai_confidence > 1:
            ai_confidence = ai_confidence / 100
        scores.append(ai_confidence)
        weights.append(2)
    
    # Factor 2: Required fields completeness (weight: 2)
    required = ['party_name', 'voucher_type', 'items', 'total_amount', 'date']
    filled = sum(1 for field in required if bill_data.get(field))
    completeness = filled / len(required)
    scores.append(completeness)
    weights.append(2)
    
    # Factor 3: Items completeness (weight: 3 - most important)
    items = bill_data.get('items', [])
    if items:
        complete_items = 0
        for item in items:
            # Critical fields for each item
            critical_fields = ['name', 'quantity', 'rate', 'amount']
            optional_fields = ['unit']  # Unit is nice-to-have
            
            critical_filled = all(item.get(k) for k in critical_fields)
            optional_filled = all(item.get(k) for k in optional_fields)
            
            if critical_filled:
                complete_items += 0.8 if optional_filled else 0.6
                complete_items += 0.2  # Base score for having critical fields
        
        item_completeness = complete_items / len(items)
        scores.append(min(1.0, item_completeness))
        weights.append(3)
    else:
        scores.append(0.0)
        weights.append(3)
    
    # Factor 4: Math validation - amounts should add up (weight: 2)
    if items:
        calculated_subtotal = sum(
            float(item.get('amount', 0) or 0) for item in items
        )
        
        # Check against subtotal or total_amount
        declared_subtotal = bill_data.get('subtotal', 0) or bill_data.get('total_amount', 0)
        
        if declared_subtotal and declared_subtotal > 0:
            # Allow 5% tolerance for rounding differences
            tolerance = declared_subtotal * 0.05
            difference = abs(calculated_subtotal - declared_subtotal)
            
            if difference <= tolerance:
                scores.append(1.0)
            elif difference <= declared_subtotal * 0.1:  # Within 10%
                scores.append(0.8)
            elif difference <= declared_subtotal * 0.2:  # Within 20%
                scores.append(0.5)
            else:
                scores.append(0.2)  # Major discrepancy
            weights.append(2)
    
    # Factor 5: GST calculation validity (weight: 1)
    subtotal = float(bill_data.get('subtotal', 0) or 0)
    gst = bill_data.get('gst', {})
    total_gst = float(gst.get('total_gst', 0) or 0) if isinstance(gst, dict) else 0
    
    if subtotal > 0 and total_gst > 0:
        # Check if GST is reasonable (5-28% range for India)
        gst_percent = (total_gst / subtotal) * 100
        
        if 5 <= gst_percent <= 28:
            scores.append(1.0)
        elif 0 < gst_percent < 5 or 28 < gst_percent <= 35:
            scores.append(0.7)  # Unusual but possible
        else:
            scores.append(0.4)  # Very unusual GST rate
        weights.append(1)
    elif subtotal > 0 and total_gst == 0:
        # No GST might be valid for exempt items
        scores.append(0.85)
        weights.append(1)
    
    # Calculate weighted average
    if scores and weights:
        total_weight = sum(weights)
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        overall = weighted_sum / total_weight
    else:
        overall = 0.0
    
    logger.info(f"📊 Confidence breakdown: scores={[round(s, 2) for s in scores]}, weights={weights}, overall={overall:.2%}")
    
    return round(overall, 3)


def identify_uncertain_fields(bill_data: Dict) -> List[str]:
    """
    Identify which fields are uncertain/missing.
    Used to generate targeted clarification questions.
    
    Returns: List of field names needing clarification
    """
    uncertain = []
    
    # Check party name
    party = bill_data.get('party_name')
    if not party or party.lower() in ['unknown', 'not found', 'unclear']:
        uncertain.append('party_name')
    
    # Check voucher type
    voucher_type = bill_data.get('voucher_type')
    if not voucher_type or voucher_type.lower() in ['unknown', 'not specified']:
        uncertain.append('voucher_type')
    
    # Check date
    date = bill_data.get('date')
    if not date:
        uncertain.append('date')
    
    # Check items
    items = bill_data.get('items', [])
    if not items:
        uncertain.append('items')
    else:
        # Check if any item is incomplete
        for i, item in enumerate(items):
            if not item.get('name') or item['name'].lower() in ['unknown', 'unclear']:
                uncertain.append(f'item_{i+1}_name')
            
            qty = item.get('quantity')
            if qty is None or (isinstance(qty, (int, float)) and qty <= 0):
                uncertain.append(f'item_{i+1}_quantity')
            
            rate = item.get('rate')
            if rate is None or (isinstance(rate, (int, float)) and rate <= 0):
                uncertain.append(f'item_{i+1}_rate')
    
    # Check total amount
    total = bill_data.get('total_amount')
    if not total or (isinstance(total, (int, float)) and total <= 0):
        uncertain.append('total_amount')
    
    return uncertain


def generate_clarification_question(uncertain_fields: List[str], bill_data: Dict) -> str:
    """
    Generate a single, targeted clarification question based on uncertain fields.
    Returns the most critical question to ask.
    """
    
    if not uncertain_fields:
        return None
    
    # Priority order for questions
    priority = [
        ('party_name', "I couldn't read the party/supplier name clearly. What is the party name?"),
        ('voucher_type', "Is this a Purchase or Sales invoice?"),
        ('date', "What is the invoice date?"),
        ('items', "I couldn't extract the items from this bill. Can you send a clearer image?"),
        ('total_amount', "What is the total amount on this invoice?"),
    ]
    
    # Check priority questions first
    for field, question in priority:
        if field in uncertain_fields:
            return question
    
    # Check for item-specific issues
    for field in uncertain_fields:
        if field.startswith('item_') and '_name' in field:
            item_num = field.split('_')[1]
            return f"What is the name of item #{item_num}?"
        if field.startswith('item_') and '_quantity' in field:
            item_num = field.split('_')[1]
            return f"What is the quantity for item #{item_num}?"
    
    # Generic fallback
    return f"Please confirm these details: {', '.join(uncertain_fields[:3])}"


def get_confidence_summary(confidence: float) -> Dict:
    """
    Get a human-readable confidence summary.
    """
    if confidence >= 0.95:
        return {
            "level": "high",
            "emoji": "🟢",
            "action": "auto_execute",
            "message": "High confidence - auto-processing"
        }
    elif confidence >= 0.75:
        return {
            "level": "medium",
            "emoji": "🟡",
            "action": "review_required",
            "message": "Medium confidence - please review"
        }
    else:
        return {
            "level": "low",
            "emoji": "🔴",
            "action": "clarification_needed",
            "message": "Low confidence - clarification needed"
        }
