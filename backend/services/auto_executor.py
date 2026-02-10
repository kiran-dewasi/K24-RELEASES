"""
Auto-Execution Service for Bill Processing
==========================================
Implements confidence-based auto-execution logic.
If confidence >= 95% → auto-create + post to Tally.
Only ask questions if truly uncertain.
"""

from typing import Dict, Optional
import logging
import os

from .confidence_scorer import (
    calculate_overall_confidence,
    identify_uncertain_fields,
    generate_clarification_question,
    get_confidence_summary
)

logger = logging.getLogger(__name__)

# Confidence thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.95  # Auto-execute without questions
MEDIUM_CONFIDENCE_THRESHOLD = 0.75  # Create draft, ask for review
# Below 0.75: Ask clarification question


async def process_with_auto_execution(
    bill_data: Dict,
    user_id: str,
    tenant_id: Optional[str] = None,
    auto_post_enabled: bool = False
) -> Dict:
    """
    Process bill with confidence-based auto-execution.
    
    Decision tree:
    - confidence >= 95%: Auto-create voucher (optionally post to Tally)
    - confidence 75-94%: Create draft, ask for confirmation
    - confidence < 75%: Ask ONE targeted clarification question
    
    Args:
        bill_data: Extracted bill data from Gemini
        user_id: User/tenant identifier
        tenant_id: Optional separate tenant ID
        auto_post_enabled: If True, push to Tally on high confidence
    
    Returns:
        Dict with:
        - action: 'auto_posted' | 'auto_created' | 'needs_review' | 'needs_clarification'
        - voucher: Created voucher data (if applicable)
        - confidence: Calculated confidence score
        - message: User-facing message
        - question: Clarification question (if needed)
    """
    
    # Calculate confidence
    confidence = calculate_overall_confidence(bill_data)
    summary = get_confidence_summary(confidence)
    
    logger.info(f"📊 Overall Confidence: {confidence:.2%} ({summary['level']})")
    
    # Get item count and total for messages
    items_count = len(bill_data.get('items', []))
    total_amount = bill_data.get('total_amount', 0) or 0
    party_name = bill_data.get('party_name', 'Unknown')
    
    # ============ DECISION TREE ============
    
    if confidence >= HIGH_CONFIDENCE_THRESHOLD:
        # 🟢 HIGH CONFIDENCE: Auto-execute without questions
        logger.info("✅ High confidence - auto-creating voucher")
        
        voucher = await _create_voucher_internal(
            bill_data, 
            user_id, 
            tenant_id,
            status='approved'
        )
        
        # Auto-post to Tally if enabled
        if auto_post_enabled:
            tally_result = await _push_to_tally_internal(voucher, tenant_id)
            
            # CHECK IF TALLY PUSH ACTUALLY SUCCEEDED
            if tally_result.get("success", False):
                return {
                    "action": "auto_posted",
                    "voucher": voucher,
                    "confidence": confidence,
                    "confidence_level": summary['level'],
                    "tally_result": tally_result,
                    "items_count": items_count,
                    "total_amount": total_amount,
                    "party_name": party_name,
                    "message": f"✅ Auto-posted to Tally! {party_name}: {items_count} items, ₹{total_amount:,.2f}"
                }
            else:
                # Tally push failed - report as created, not posted
                logger.warning(f"⚠️ Tally push failed: {tally_result.get('error', 'Unknown error')}")
                return {
                    "action": "auto_created",  # NOT auto_posted since Tally failed
                    "voucher": voucher,
                    "confidence": confidence,
                    "confidence_level": summary['level'],
                    "tally_result": tally_result,
                    "tally_error": tally_result.get('error'),
                    "items_count": items_count,
                    "total_amount": total_amount,
                    "party_name": party_name,
                    "message": f"✅ Voucher created but Tally offline. {party_name}: {items_count} items, ₹{total_amount:,.2f}"
                }
        else:
            return {
                "action": "auto_created",
                "voucher": voucher,
                "confidence": confidence,
                "confidence_level": summary['level'],
                "items_count": items_count,
                "total_amount": total_amount,
                "party_name": party_name,
                "message": f"✅ Voucher created! {party_name}: {items_count} items, ₹{total_amount:,.2f}"
            }
    
    elif confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
        # 🟡 MEDIUM CONFIDENCE: Create draft, ask for confirmation
        logger.info("⚠️ Medium confidence - creating draft for review")
        
        voucher = await _create_voucher_internal(
            bill_data, 
            user_id,
            tenant_id,
            status='draft'
        )
        
        uncertain = identify_uncertain_fields(bill_data)
        
        # Format uncertain fields for display
        uncertain_display = []
        for field in uncertain[:3]:  # Show max 3
            if 'item_' in field:
                parts = field.split('_')
                uncertain_display.append(f"Item {parts[1]} {parts[2]}")
            else:
                uncertain_display.append(field.replace('_', ' ').title())
        
        review_note = f"Uncertain: {', '.join(uncertain_display)}" if uncertain_display else "Please review before posting"
        
        return {
            "action": "needs_review",
            "voucher": voucher,
            "confidence": confidence,
            "confidence_level": summary['level'],
            "uncertain_fields": uncertain,
            "items_count": items_count,
            "total_amount": total_amount,
            "party_name": party_name,
            "message": f"⚠️ Draft created ({confidence:.0%} confidence). {review_note}"
        }
    
    else:
        # 🔴 LOW CONFIDENCE: Ask ONE targeted question
        logger.info("❌ Low confidence - asking for clarification")
        
        uncertain = identify_uncertain_fields(bill_data)
        question = generate_clarification_question(uncertain, bill_data)
        
        return {
            "action": "needs_clarification",
            "confidence": confidence,
            "confidence_level": summary['level'],
            "partial_data": bill_data,
            "uncertain_fields": uncertain,
            "question": question,
            "items_count": items_count,
            "total_amount": total_amount,
            "party_name": party_name,
            "message": f"❓ {question}"
        }


async def _create_voucher_internal(
    bill_data: Dict, 
    user_id: str,
    tenant_id: Optional[str],
    status: str = 'draft'
) -> Dict:
    """
    Internal helper to create voucher from bill data.
    Wraps the actual voucher creation logic.
    """
    try:
        # Try to use existing voucher creation logic
        from backend.logic import logic_create_voucher_async
        
        # Transform bill_data to voucher format
        voucher_data = {
            "voucher_type": bill_data.get('voucher_type', 'Purchase'),
            "party_name": bill_data.get('party_name', 'Unknown Party'),
            "date": bill_data.get('date'),
            "invoice_number": bill_data.get('invoice_number'),
            "narration": f"Auto-created from bill image",
            "status": status,
            "line_items": bill_data.get('items', []),
            "subtotal": bill_data.get('subtotal'),
            "gst": bill_data.get('gst', {}),
            "total_amount": bill_data.get('total_amount'),
            "confidence": bill_data.get('confidence')
        }
        
        result = await logic_create_voucher_async(
            voucher_data,
            user_id=user_id,
            thread_id=tenant_id
        )
        
        return result
        
    except ImportError as e:
        logger.warning(f"Voucher creation function not available: {e}")
        # Return mock voucher for development
        return {
            "id": f"VOUCHER-{os.urandom(4).hex().upper()}",
            "status": status,
            "party_name": bill_data.get('party_name'),
            "total_amount": bill_data.get('total_amount'),
            "items_count": len(bill_data.get('items', [])),
            "note": "Mock voucher - production integration pending"
        }
    except Exception as e:
        logger.error(f"Failed to create voucher: {e}")
        return {
            "error": str(e),
            "status": "error"
        }


async def _push_to_tally_internal(voucher: Dict, tenant_id: Optional[str]) -> Dict:
    """
    Internal helper to push voucher to Tally.
    """
    try:
        from backend.tally_live_update import create_voucher_safely
        import json
        from datetime import datetime
        
        # Get company name from config file or env
        company = os.getenv("TALLY_COMPANY", "Default Company")
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'k24_config.json')
            if os.path.exists(config_path):
                with open(config_path) as f:
                    config = json.load(f)
                    company = config.get('company_name', company)
        except:
            pass
        
        logger.info(f"🏢 Using company: {company}")
        
        # Format date to YYYYMMDD (8 chars required by Tally)
        raw_date = voucher.get('date', '')
        if raw_date:
            try:
                # Try parsing common formats
                if isinstance(raw_date, str):
                    if len(raw_date) == 8 and raw_date.isdigit():
                        tally_date = raw_date  # Already YYYYMMDD
                    elif '-' in raw_date:
                        dt = datetime.strptime(raw_date[:10], '%Y-%m-%d')
                        tally_date = dt.strftime('%Y%m%d')
                    elif '/' in raw_date:
                        dt = datetime.strptime(raw_date[:10], '%d/%m/%Y')
                        tally_date = dt.strftime('%Y%m%d')
                    else:
                        tally_date = datetime.now().strftime('%Y%m%d')
                else:
                    tally_date = datetime.now().strftime('%Y%m%d')
            except:
                tally_date = datetime.now().strftime('%Y%m%d')
        else:
            tally_date = datetime.now().strftime('%Y%m%d')
        
        logger.info(f"📅 Date formatted: {raw_date} -> {tally_date}")
        
        # Prepare Tally format - use CORRECT key casing for create_voucher_safely
        voucher_fields = {
            "Date": tally_date,  # Must be YYYYMMDD
            "PartyLedgerName": voucher.get('party_name', ''),
            "Narration": voucher.get('narration', 'Auto-posted from K24'),
        }
        
        line_items = voucher.get('line_items', [])
        
        logger.info(f"📦 Pushing voucher: {voucher_fields['PartyLedgerName']}, {len(line_items)} items")
        
        # Extract Taxes
        gst_data = voucher.get('gst', {})
        taxes = []
        if gst_data:
             for k, v in gst_data.items():
                 # Filter numeric values
                 try:
                     val = float(v)
                     if val > 0:
                         # Map 'cgst' -> 'CGST', etc.
                         ledger_name = k.upper()
                         # If key is like 'cgst_rate', skip
                         if 'RATE' in ledger_name: continue
                         
                         taxes.append({"ledger": ledger_name, "amount": val})
                 except: pass
        
        result = create_voucher_safely(
            company=company,
            voucher_type=voucher.get('voucher_type', 'Purchase'),
            voucher_fields=voucher_fields,
            line_items=line_items,
            taxes=taxes
        )
        
        logger.info(f"📤 Tally result: success={result.success}, error={result.error_details}")
        
        return {
            "success": result.success if hasattr(result, 'success') else True,
            "tally_response": result.to_dict() if hasattr(result, 'to_dict') else str(result),
            "error": result.error_details if hasattr(result, 'error_details') and not result.success else None
        }
        
    except ImportError as e:
        logger.warning(f"Tally integration not available: {e}")
        return {"success": False, "error": "Tally integration not configured"}
    except Exception as e:
        logger.error(f"Failed to push to Tally: {e}")
        return {"success": False, "error": str(e)}


def process_with_auto_execution_sync(
    bill_data: Dict,
    user_id: str,
    tenant_id: Optional[str] = None,
    auto_post_enabled: bool = False
) -> Dict:
    """
    Synchronous wrapper for process_with_auto_execution.
    Use this from non-async code.
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context, create a new loop
            import nest_asyncio
            nest_asyncio.apply()
        return loop.run_until_complete(
            process_with_auto_execution(bill_data, user_id, tenant_id, auto_post_enabled)
        )
    except RuntimeError:
        # No event loop exists, create one
        return asyncio.run(
            process_with_auto_execution(bill_data, user_id, tenant_id, auto_post_enabled)
        )
