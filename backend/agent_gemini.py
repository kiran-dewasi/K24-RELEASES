# K24 AI Agent - Gemini XML Generator
# ====================================
# Uses Gemini to generate Tally-compliant XML for vouchers
# Integrated with GeminiOrchestrator for robust handling

from typing import Dict, Any, Optional, Tuple, List
import logging
import xml.etree.ElementTree as ET
import os
import re
import json
import asyncio
from datetime import datetime
from PIL import Image

from backend.gemini.gemini_orchestrator import GeminiOrchestrator

logger = logging.getLogger(__name__)


class XMLGenerationError(Exception):
    """Custom exception for XML generation failures"""
    pass


class GeminiXMLAgent:
    """
    Generates Tally-compliant XML using Gemini.
    Includes schema validation and retry logic.
    """
    
    def __init__(self, api_key: str = None, model_name: str = "gemini-1.5-flash"):
        """Initialize with Gemini Orchestrator"""
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY must be provided")
        
        # Initialize orchestrator with XML-specific system prompt
        self.orchestrator = GeminiOrchestrator(
            api_key=self.api_key,
            system_prompt="You are a Tally XML expert. Output ONLY valid XML."
        )
        print(f"[AGENT] GeminiXMLAgent initialized with model: {model_name}")
    
    async def generate_voucher_xml(
        self,
        voucher_type: str,
        party_name: str,
        amount: float,
        date: str = None,
        narration: str = "",
        additional_params: Dict[str, Any] = None
    ) -> Tuple[bool, str, List[str]]:
        """
        Generate Tally voucher XML.
        Returns: (success, xml_string, errors)
        """
        
        # Normalize inputs
        date = date or datetime.now().strftime("%Y%m%d")
        additional_params = additional_params or {}
        
        # Build prompt
        prompt = self._build_xml_prompt(
            voucher_type=voucher_type,
            party_name=party_name,
            amount=amount,
            date=date,
            narration=narration,
            additional_params=additional_params
        )
        
        try:
            # Generate XML using Orchestrator
            # System prompt is already set in __init__
            response_text = await self.orchestrator.invoke_with_retry(
                query=prompt
            )
            
            # Clean response
            xml_text = self._clean_xml_response(response_text)
            
            # Validate
            is_valid, errors = self._validate_xml(xml_text)
            
            if is_valid:
                logger.info(f"Successfully generated XML for {voucher_type}")
                return (True, xml_text, [])
            else:
                logger.warning(f"Generated XML has validation errors: {errors}")
                
                # Attempt to fix
                logger.info("Attempting to fix XML...")
                return await self.regenerate_with_fixes(xml_text, errors, prompt)
        
        except Exception as e:
            logger.error(f"XML generation failed: {e}")
            return (False, "", [str(e)])
    
    def _build_xml_prompt(
        self,
        voucher_type: str,
        party_name: str,
        amount: float,
        date: str,
        narration: str,
        additional_params: Dict[str, Any]
    ) -> str:
        """Build the Gemini prompt for XML generation"""
        
        # Get deposit account (Cash or Bank)
        deposit_to = additional_params.get("deposit_to", "Cash")
        tax_rate = additional_params.get("tax_rate", 0)
        company_name = additional_params.get("company_name", "Krishasales")
        
        # Calculate tax amount if applicable
        tax_amount = 0
        if tax_rate > 0:
            tax_amount = amount * (tax_rate / 100)
            total_amount = amount + tax_amount
        else:
            total_amount = amount
        
        prompt = f"""You are a Tally XML expert. Generate ONLY valid Tally XML for this voucher.

VOUCHER DETAILS:
- Type: {voucher_type}
- Party Name: {party_name}
- Amount: ₹{amount:.2f}
- {'Tax: ' + str(tax_rate) + '% GST (₹' + str(tax_amount) + ')' if tax_rate > 0 else 'No Tax'}
- {'Total Amount: ₹' + str(total_amount) if tax_rate > 0 else ''}
- Date: {date} (YYYYMMDD format)
- Narration: {narration or 'Created via K24'}
- {'Deposit To: ' + deposit_to if voucher_type in ['Receipt', 'Payment'] else ''}
- Company: {company_name}

STRICT REQUIREMENTS:
1. Use EXACT Tally XML schema for vouchers
2. Format ALL amounts as strings with 2 decimal places (e.g., "50000.00")
3. Use YYYYMMDD date format ONLY
4. Include PROPER ledger entries:
   - For Receipt: Debit {deposit_to}, Credit {party_name}
   - For Payment: Debit {party_name}, Credit {deposit_to}
   - For Sales: Debit {party_name}, Credit Sales Account
5. Use ISDEEMEDPOSITIVE correctly (Yes for debit, No for credit)
6. Include GUID for tracking (generate unique GUID)
7. Ledger names MUST match exactly as provided

XML TEMPLATE STRUCTURE:
<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Import Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Vouchers</REPORTNAME>
        <STATICVARIABLES>
          <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
        </STATICVARIABLES>
      </REQUESTDESC>
      <REQUESTDATA>
        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          <VOUCHER ACTION="Create">
            <DATE>{date}</DATE>
            <VOUCHERTYPENAME>{voucher_type}</VOUCHERTYPENAME>
            <NARRATION>{narration or 'Created via K24'}</NARRATION>
            <ALLLEDGERENTRIES.LIST>
              <!-- First Ledger Entry -->
            </ALLLEDGERENTRIES.LIST>
            <ALLLEDGERENTRIES.LIST>
              <!-- Second Ledger Entry -->
            </ALLLEDGERENTRIES.LIST>
          </VOUCHER>
        </TALLYMESSAGE>
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>

IMPORTANT RULES:
- Amount values MUST be numeric strings with exactly 2 decimal places
- Positive amounts are DEBIT, Negative amounts are CREDIT
- ISDEEMEDPOSITIVE="Yes" means DEBIT side
- ISDEEMEDPOSITIVE="No" means CREDIT side
- Amounts must balance (sum to zero)
- NO explanations, ONLY pure XML
- NO markdown code blocks, ONLY XML
- XML must be valid and well-formed

Generate the complete XML now:"""

        return prompt
    
    def _clean_xml_response(self, xml_text: str) -> str:
        """Clean Gemini response to extract pure XML"""
        
        # Remove markdown code blocks if present
        if "```xml" in xml_text:
            xml_text = xml_text.split("```xml", 1)[1]
            xml_text = xml_text.split("```", 1)[0]
        elif "```" in xml_text:
            xml_text = xml_text.split("```", 1)[1]
            xml_text = xml_text.split("```", 1)[0]
        
        # Remove any explanatory text before <ENVELOPE>
        envelope_match = re.search(r'<ENVELOPE>.*</ENVELOPE>', xml_text, re.DOTALL)
        if envelope_match:
            xml_text = envelope_match.group(0)
        
        # Clean whitespace
        xml_text = xml_text.strip()
        
        return xml_text
    
    def _validate_xml(self, xml_text: str) -> Tuple[bool, List[str]]:
        """
        Validate XML structure and Tally-specific requirements.
        Returns: (is_valid, error_messages)
        """
        errors = []
        
        # Check 1: Valid XML syntax
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            errors.append(f"XML Parse Error: {str(e)}")
            return (False, errors)
        
        # Check 2: Required root elements
        if root.tag != "ENVELOPE":
            errors.append("Root element must be <ENVELOPE>")
        
        header = root.find("HEADER")
        if header is None:
            errors.append("Missing <HEADER> element")
        
        body = root.find("BODY")
        if body is None:
            errors.append("Missing <BODY> element")
            return (False, errors)
        
        # Check 3: IMPORTDATA structure
        importdata = body.find("IMPORTDATA")
        if importdata is None:
            errors.append("Missing <IMPORTDATA> element")
            return (False, errors)
        
        # Check 4: REQUESTDATA and TALLYMESSAGE
        requestdata = importdata.find("REQUESTDATA")
        if requestdata is None:
            errors.append("Missing <REQUESTDATA> element")
            return (False, errors)
        
        tallymessage = requestdata.find("TALLYMESSAGE")
        if tallymessage is None:
            errors.append("Missing <TALLYMESSAGE> element")
            return (False, errors)
        
        # Check 5: VOUCHER element
        voucher = tallymessage.find("VOUCHER")
        if voucher is None:
            errors.append("Missing <VOUCHER> element")
            return (False, errors)
        
        # Check 6: Required voucher fields
        required_fields = ["DATE", "VOUCHERTYPENAME"]
        for field in required_fields:
            if voucher.find(field) is None:
                errors.append(f"Missing required field: <{field}>")
        
        # Check 7: Ledger entries
        ledger_entries = voucher.findall(".//ALLLEDGERENTRIES.LIST")
        if len(ledger_entries) < 2:
            errors.append(f"Need at least 2 ledger entries, found {len(ledger_entries)}")
        
        # Check 8: Amount balancing
        total_amount = 0.0
        for entry in ledger_entries:
            amount_elem = entry.find("AMOUNT")
            if amount_elem is not None and amount_elem.text:
                try:
                    amount = float(amount_elem.text)
                    total_amount += amount
                except ValueError:
                    errors.append(f"Invalid amount format: {amount_elem.text}")
        
        # Amounts should sum to zero (within floating point tolerance)
        if abs(total_amount) > 0.01:
            errors.append(f"Amounts don't balance: total = {total_amount}")
        
        # Check 9: Amount formatting (should have 2 decimal places)
        for entry in ledger_entries:
            amount_elem = entry.find("AMOUNT")
            if amount_elem is not None and amount_elem.text:
                if '.' in amount_elem.text:
                    decimal_part = amount_elem.text.split('.')[1]
                    if len(decimal_part) != 2:
                        errors.append(f"Amount should have exactly 2 decimal places: {amount_elem.text}")
        
        is_valid = len(errors) == 0
        return (is_valid, errors)
    
    async def regenerate_with_fixes(
        self,
        original_xml: str,
        validation_errors: List[str],
        original_prompt: str
    ) -> Tuple[bool, str, List[str]]:
        """
        Attempt to fix XML by asking Gemini to regenerate with error feedback.
        """
        
        fix_prompt = f"""{original_prompt}

PREVIOUS ATTEMPT HAD THESE ERRORS:
{chr(10).join(f"- {error}" for error in validation_errors)}

Fix these errors and generate corrected XML. Remember:
- Amounts must be formatted with exactly 2 decimal places
- All ledger entries must have LEDGERNAME, AMOUNT, ISDEEMEDPOSITIVE
- Amounts must balance to zero
- Use proper Tally schema

Generate the CORRECTED XML now (XML only, no explanations):"""

        try:
            response_text = await self.orchestrator.invoke_with_retry(
                query=fix_prompt
            )
            
            xml_text = self._clean_xml_response(response_text)
            
            is_valid, new_errors = self._validate_xml(xml_text)
            
            return (is_valid, xml_text, new_errors)
        except Exception as e:
            logger.error(f"XML regeneration failed: {e}")
            return (False, "", [str(e)])



ENHANCED_MULTI_ITEM_PROMPT = """
You are an expert invoice data extractor for Indian accounting systems. Your task is to extract EVERY line item from an invoice table with 100% accuracy.

CRITICAL RULES FOR LARGE INVOICES:
1. SCAN THE ENTIRE IMAGE - do not stop at 5-6 items even if the list is long
2. Look for tabular data with columns: Item/Description, Qty, Rate, Amount
3. Each ROW in the item table = 1 separate item in your output
4. If you see "..." or continuation indicators, process ALL visible items
5. Count the total rows carefully before starting extraction

FIELD EXTRACTION PRIORITY:
High Priority (MUST extract):
- Item name/description
- Quantity (if missing, assume 1)
- Rate/Price per unit
- Line total amount

Medium Priority (extract if present):
- Unit of measurement (Nos, Kgs, Ltr, Pcs, Box, Mtr)
- HSN/SAC code
- Discount percentage

Low Priority (optional):
- Item code/SKU
- Tax rate per item

UNIT DETECTION RULES:
- Look for units in: column headers, item descriptions, or quantity field
- Common patterns: "10 Nos", "5 Kgs", "2.5 Ltr"
- If unit is ANYWHERE near the item, extract it
- If completely missing, use "Kgs" as default
- Never use "Unknown" or null for units

JSON OUTPUT FORMAT (STRICT):
{
  "voucher_type": "Purchase" | "Sales",
  "confidence": 0.XX,  // 0.95+ for clear bills, 0.70-0.94 for partial clarity
  "party_name": "Exact supplier/customer name from bill",
  "bill_number": "Invoice number",
  "date": "YYYY-MM-DD",
  "items": [
    {
      "sr_no": 1,  // Sequential number (helps verify completeness)
      "name": "Full item description",
      "hsn_code": "1234" | null,
      "quantity": 10.5,
      "unit": "Kgs",  // NEVER null, use "Kgs" if unclear
      "rate": 500.00,
      "amount": 5250.00,
      "discount_percent": 0 | 10,
      "taxable_amount": 5250.00
    }
    // ... continue for ALL items in the bill
  ],
  "items_count": 10,  // Total items you extracted (self-verification)
  "subtotal": 52500.00,
  "gst": {
    "cgst": 4725.00,
    "sgst": 4725.00,
    "igst": 0,
    "total_gst": 9450.00
  },
  "total_amount": 61950.00,
  "payment_mode": "Cash" | "Credit" | null
}

QUALITY CHECKS (Self-verify before responding):
1. Did I extract the SAME number of items as rows in the bill's item table?
2. Does the sum of all item amounts match the subtotal?
3. Do all items have non-null units?
4. Are quantities and rates reasonable (no obvious OCR errors like "10000" instead of "100.00")?

If you cannot see all items clearly (image cut off, blurry), set confidence to 0.50-0.70 and include a "warning" field.

Now extract data from this invoice image. Return ONLY valid JSON, no markdown formatting:
"""

COMMON_UNITS = ['Nos', 'Kgs', 'Ltr', 'Mtr', 'Box', 'Pcs', 'Pkt', 'Bag', 'Set', 'Doz', 'Gm', 'Ml', 'Kg', 'Pc']

def fix_missing_units(bill_data: dict) -> dict:
    """
    Apply smart unit detection + Kgs default for all items.
    Ensures EVERY item has a valid unit for Tally compatibility.
    """
    for item in bill_data.get('items', []):
        unit = str(item.get('unit', '') or '').strip()
        
        # Check if unit is missing or invalid
        if not unit or unit.lower() in ['null', 'unknown', '', 'na', 'none', '-']:
            # Try to infer from item name
            name_lower = str(item.get('name', '')).lower()
            
            # Weight-based items
            if any(x in name_lower for x in ['kg', 'kilo', 'weight', 'gram', 'gm']):
                if 'gram' in name_lower or 'gm' in name_lower:
                    item['unit'] = 'Gm'
                else:
                    item['unit'] = 'Kgs'
            # Liquid items
            elif any(x in name_lower for x in ['liter', 'ltr', 'litre', 'ml', 'liquid', 'oil']):
                if 'ml' in name_lower:
                    item['unit'] = 'Ml'
                else:
                    item['unit'] = 'Ltr'
            # Length measurement
            elif any(x in name_lower for x in ['meter', 'mtr', 'feet', 'ft', 'inch']):
                item['unit'] = 'Mtr'
            # Count/Piece items
            elif any(x in name_lower for x in ['piece', 'pcs', 'nos', 'number', 'unit']):
                item['unit'] = 'Nos'
            # Package items
            elif any(x in name_lower for x in ['box', 'carton', 'pack', 'packet', 'pkt']):
                if 'pack' in name_lower or 'pkt' in name_lower:
                    item['unit'] = 'Pkt'
                else:
                    item['unit'] = 'Box'
            elif 'set' in name_lower:
                item['unit'] = 'Set'
            elif 'dozen' in name_lower or 'doz' in name_lower:
                item['unit'] = 'Doz'
            else:
                # Default fallback
                item['unit'] = 'Kgs'
                logger.warning(f"Applied default 'Kgs' to: {item.get('name')}")
        
        # Normalize existing units to standard format
        else:
            unit_lower = unit.lower()
            unit_mapping = {
                'kg': 'Kgs', 'kgs': 'Kgs', 'kilogram': 'Kgs',
                'gm': 'Gm', 'gram': 'Gm', 'grams': 'Gm', 'g': 'Gm',
                'ltr': 'Ltr', 'liter': 'Ltr', 'litre': 'Ltr', 'l': 'Ltr',
                'ml': 'Ml', 'milliliter': 'Ml',
                'mtr': 'Mtr', 'meter': 'Mtr', 'm': 'Mtr',
                'nos': 'Nos', 'no': 'Nos', 'number': 'Nos', 'num': 'Nos',
                'pcs': 'Pcs', 'pc': 'Pcs', 'piece': 'Pcs', 'pieces': 'Pcs',
                'box': 'Box', 'boxes': 'Box',
                'pkt': 'Pkt', 'packet': 'Pkt', 'pack': 'Pkt',
                'bag': 'Bag', 'bags': 'Bag',
                'set': 'Set', 'sets': 'Set',
                'doz': 'Doz', 'dozen': 'Doz',
            }
            item['unit'] = unit_mapping.get(unit_lower, unit.capitalize())
    
    return bill_data


def validate_and_fix_extraction(data: dict) -> dict:
    """
    Post-process Gemini output to fix common errors
    """
    if "error" in data:
        return data
    
    # Fix 0: Apply smart unit detection first
    data = fix_missing_units(data)
        
    # Fix 1: Ensure all items have units (double-check after fix_missing_units)
    for item in data.get('items', []):
        if not item.get('unit') or item['unit'] in ['', 'null', 'Unknown']:
            item['unit'] = 'Kgs'
            logger.warning(f"Applied default unit 'Kgs' to item: {item.get('name')}")
    
    # Fix 2: Verify item count matches
    declared_count = data.get('items_count')
    actual_count = len(data.get('items', []))
    
    if declared_count is not None and declared_count != actual_count:
        logger.warning(f"Count mismatch: AI said {declared_count}, found {actual_count}")
        data['confidence'] = max(0.50, data.get('confidence', 0.90) - 0.15)
    
    # Fix 3: Verify amounts add up
    calculated_subtotal = sum(item.get('amount', 0) for item in data.get('items', []))
    declared_subtotal = data.get('subtotal')
    
    if declared_subtotal:
        difference = abs(calculated_subtotal - declared_subtotal)
        if difference > 1:  # Allow 1 rounding error
            logger.warning(f"Subtotal mismatch: Items sum to {calculated_subtotal}, bill says {declared_subtotal}")
            data['confidence'] = max(0.60, data.get('confidence', 0.90) - 0.10)
    
    # Fix 4: Catch OCR errors in rates (e.g., 10000 instead of 100.00)
    for item in data.get('items', []):
        rate = item.get('rate', 0)
        qty = item.get('quantity', 1)
        amount = item.get('amount', 0)
        
        # If rate * qty doesn't match amount, likely OCR error
        if rate and qty:
            expected_amount = rate * qty
            if abs(expected_amount - amount) > amount * 0.1:  # 10% tolerance
                logger.warning(f"Rate/Qty/Amount mismatch for {item.get('name')}")
                # Try to recalculate rate
                if qty > 0:
                    item['rate'] = round(amount / qty, 2)
                    logger.warning(f"   Auto-corrected rate to: {item['rate']}")
    
    return data

def extract_bill_data(
    image_path: str,
    api_key: str,
    tenant_id: Optional[str] = None,    # ← for credit + LLM tracking
    page_count: int = 1,                 # ← how many pages in this document
) -> dict:
    """
    Optimized for large invoices with many items.
    Fires DOCUMENT/page_processed credit event per page on successful extraction.
    Logs LLM token usage for cost analytics.
    """
    import google.generativeai as genai
    
    # Configure inside function to ensure api_key is applied
    genai.configure(api_key=api_key)
    
    # Use the most capable model
    model = genai.GenerativeModel(
        'gemini-2.0-flash',
        generation_config={
            "temperature": 0.1,  # Low temp for precision
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,  # Allow longer responses for 15+ items
        }
    )
    
    # Load image (support multiple formats)
    from pathlib import Path
    
    try:
        image_bytes = Path(image_path).read_bytes()
    except Exception as e:
        logger.error(f"Failed to load image: {e}")
        return {"items": [], "error": f"Image load failed: {e}"}
    
    # Detect mime type
    if image_path.lower().endswith('.png'):
        mime_type = "image/png"
    elif image_path.lower().endswith(('.jpg', '.jpeg')):
        mime_type = "image/jpeg"
    try:
        # Retry logic for 429 errors
        import time
        max_retries = 3
        retry_delay = 2  # start with 2 seconds backoff
        
        if tenant_id:
            from backend.credit_engine.engine import check_credits_available
            from fastapi import HTTPException
            if not check_credits_available(tenant_id, "DOCUMENT"):
                raise HTTPException(status_code=402, detail="Credit limit reached")
        
        response = None
        for attempt in range(max_retries):
            try:
                # Call API
                # Pass the ENHANCED_MULTI_ITEM_PROMPT defined in this module
                response = model.generate_content([
                    ENHANCED_MULTI_ITEM_PROMPT,
                    {"mime_type": mime_type, "data": image_bytes}
                ])
                break  # Success!
            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Gemini 429 Limit hit. Retrying in {retry_delay}s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Gemini API failed after {attempt+1} attempts: {e}")
                    raise e
        
        if not response:
             raise Exception("Failed to get response from Gemini")

        # ── LLM call logging + DOCUMENT credit event ─────────────────────────────────────
        usage_event_id = None
        if tenant_id:
            try:
                # 1. Fire credit event for document processing
                from backend.credit_engine import record_event
                decision = record_event(
                    tenant_id     = tenant_id,
                    event_type    = "DOCUMENT",
                    event_subtype = "page_processed",
                    source        = "api",
                    metadata      = {"image_path": image_path, "page_count": page_count, "model": "gemini-2.0-flash"},
                )
                usage_event_id = decision.event_id
                logger.info(f"[CreditHook] DOCUMENT event | tenant={tenant_id} | status={decision.status}")
            except Exception as ce:
                logger.warning(f"[CreditHook] Document credit event failed (non-fatal): {ce}")

            try:
                # 2. Log LLM token usage
                from backend.credit_engine import log_llm_call
                usage_meta = response.usage_metadata
                log_llm_call(
                    tenant_id      = tenant_id,
                    model          = "gemini-2.0-flash",
                    workflow       = "bill_extraction",
                    tokens_input   = getattr(usage_meta, "prompt_token_count", 0) or 0,
                    tokens_output  = getattr(usage_meta, "candidates_token_count", 0) or 0,
                    usage_event_id = usage_event_id,
                )
            except Exception as le:
                logger.warning(f"[LLMLogger] Token logging failed (non-fatal): {le}")
        # ─────────────────────────────────────────────────────────────────────────────

        # Parse response
        text = response.text.strip()
        text = re.sub(r'```json\n?', '', text)
        text = re.sub(r'```\n?', '', text)
        
        # Clean potential markdown headers before JSON if any (though regex handles blocks)
        if text.startswith('json'):
            text = text[4:].strip()
            
        data = json.loads(text)
        
        # Apply validation and fixes
        data = validate_and_fix_extraction(data)
        
        return data

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return {"items": [], "error": str(e)}
