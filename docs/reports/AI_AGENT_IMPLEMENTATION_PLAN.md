# 🚀 K24 AI Agent Response Pipeline - Implementation Plan
**Status**: IN PROGRESS  
**Target**: Production-Ready Error-Resilient AI Agent  
**Last Updated**: 2025-12-02

---

## ✅ Completed

### 1. Error Handling System (`agent_errors.py`)
- ✅ Typed error codes (ValidationError, SystemError, FinancialError)
- ✅ Error severity levels (LOW, MEDIUM, HIGH, CRITICAL)
- ✅ Structured error responses with retry logic
- ✅ Context-aware error messages
- ✅ Error factory pattern

### 2. Validation Layer (`agent_validator.py`)
- ✅ Ledger validation with fuzzy matching
- ✅ Amount validation (range, format, suspicious amounts)
- ✅ Date validation and normalization
- ✅ Voucher type validation
- ✅ Financial risk checks
- ✅ Required fields validation
- ✅ Confidence scoring

---

## 🔄 Next Steps

### 3. LangGraph State Machine (`agent_graph.py`)
**Purpose**: Orchestrate the entire agent flow with explicit state management

```python
States:
1. PARSE_INTENT → Extract what user wants
2. VALIDATE_PARAMS → Safety checks
3. GENERATE_XML → Gemini creates Tally XML
4. VALIDATE_XML → Schema validation
5. DRY_RUN → Preview transaction
6. AWAIT_APPROVAL → User confirms
7. EXECUTE_TALLY → Write to Tally
8. VERIFY → Confirm success
9. RESPOND → Send result to user
10. ERROR → Handle failures

Transitions:
- If validation fails → ERROR
- If XML invalid → GENERATE_XML (retry)
- If user rejects → RESPOND (cancel)
- If Tally fails → ERROR → Fallback/Retry
```

### 4. Intent Classifier (`agent_intent.py`)
**Purpose**: Parse user commands into structured intents

**Supported Intents**:
- `create_invoice` - Create sales invoice
- `create_receipt` - Record customer payment
- `create_payment` - Record vendor payment
- `query_data` - Read-only queries
- `audit_transactions` - Compliance checks

**Output Format**:
```json
{
  "intent": "create_invoice",
  "confidence": 0.95,
  "parameters": {
    "party_name": "HDFC Bank",
    "amount": 50000,
    "tax_rate": 18,
    "narration": "Professional fees"
  }
}
```

### 5. Gemini Agent (`agent_gemini.py`)
**Purpose**: Generate Tally-compliant XML using Gemini

**Features**:
- Schema-aware XML generation
- Retry logic for malformed XML
- Temperature control for consistency
- Prompt engineering for accuracy

**Prompt Template**:
```
You are a Tally XML expert. Generate ONLY valid XML for this voucher:
- Party: {party_name}
- Amount: {amount}
- Date: {date}
- Type: {voucher_type}

Requirements:
1. Use exact Tally schema
2. Format amounts with 2 decimal places
3. Use YYYYMMDD date format
4. Include GUID for tracking

Output ONLY the XML, no explanations.
```

### 6. Error Handler (`agent_error_handler.py`)
**Purpose**: Implement retry policies and fallback strategies

**Retry Policies**:
```python
RETRY_CONFIG = {
    "GEMINI_API_TIMEOUT": {
        "max_attempts": 3,
        "backoff": "exponential",  # 1s, 2s, 4s
        "fallback": "use_template_xml"
    },
    "TALLY_CONNECTION_FAILED": {
        "max_attempts": 2,
        "backoff": "linear",  # 2s, 4s
        "fallback": "queue_for_later"
    },
    "XML_VALIDATION_FAILED": {
        "max_attempts": 2,
        "backoff": "none",
        "fallback": "manual_entry_form"
    }
}
```

### 7. Transaction Manager (`agent_transaction.py`)
**Purpose**: Handle Tally writes with rollback capability

**Features**:
- Transaction locking
- Pre-write backup
- Post-write verification
- Automatic rollback on failure
- Audit trail logging

**Flow**:
```
1. Lock transaction
2. Backup current state
3. Generate unique TXN_ID
4. Push to Tally
5. Wait for response (max 5s)
6. Verify in Tally
7. Unlock & log
8. If any step fails → Rollback
```

### 8. API Endpoints (`routers/agent.py`)
**Purpose**: Expose agent functions to frontend

**Endpoints**:
```python
POST /api/v1/agent/chat
- Input: { "message": "create invoice for ...", "context": {} }
- Output: { "status": "...", "result": {}, "preview": {} }

POST /api/v1/agent/approve
- Input: { "transaction_id": "TXN_001", "approved": true }
- Output: { "status": "SUCCESS", "tally_reference": "..." }

GET /api/v1/agent/preview/{transaction_id}
- Output: { "preview": {}, "risk_level": "LOW" }
```

### 9. Audit Logger (`agent_audit.py`)
**Purpose**: Log every agent action for compliance

**Log Format**:
```json
{
  "transaction_id": "TXN_20251202_00001",
  "timestamp": "2025-12-02T00:15:30Z",
  "user_id": "KITTU",
  "intent": "create_invoice",
  "parameters": { "party": "...", "amount": "..." },
  "validation_result": { "is_valid": true, "warnings": [] },
  "tally_response": { "status": "SUCCESS" },
  "duration_ms": 1250,
  "ip_address": "192.168.1.100"
}
```

### 10. Response Formatter (`agent_response.py`)
**Purpose**: Format agent outputs for frontend consumption

**Success Response**:
```json
{
  "status": "SUCCESS",
  "transaction_id": "TXN_20251202_00001",
  "message": "Invoice created successfully",
  "details": {
    "customer": "HDFC Bank",
    "amount": "₹59,000",
    "date": "2025-12-02",
    "invoice_number": "INV-001"
  },
  "audit_trail": {
    "created_by": "KITTU",
    "timestamp": "2025-12-02T00:15:30Z"
  }
}
```

**Error Response**:
```json
{
  "status": "FAILED",
  "error_code": "LEDGER_NOT_FOUND",
  "message": "Ledger 'HDFC Bank' not found",
  "suggestions": [
    "Did you mean 'HDFC Bank A/c 123'?",
    "Create ledger in Tally first"
  ],
  "retry_available": true
}
```

---

## 📊 Implementation Priority

| Priority | Component | Status | ETA |
|----------|-----------|--------|-----|
| P0 | Error System | ✅ Done | - |
| P0 | Validator | ✅ Done | - |
| P0 | LangGraph State Machine | 🔄 Next | 30 min |
| P1 | Intent Classifier | ⏳ Pending | 20 min |
| P1 | Gemini Agent | ⏳ Pending | 25 min |
| P1 | Error Handler | ⏳ Pending | 15 min |
| P2 | Transaction Manager | ⏳ Pending | 30 min |
| P2 | API Endpoints | ⏳ Pending | 20 min |
| P3 | Audit Logger | ⏳ Pending | 15 min |
| P3 | Response Formatter | ⏳ Pending | 10 min |

**Total Estimated Time**: ~2 hours 45 minutes

---

## 🎯 Success Criteria

When a user types: **"create invoice for HDFC Bank for ₹50,000 with 18% GST"**

The system MUST:
1. ✅ Parse intent → `create_invoice`
2. ✅ Extract params → `{party: "HDFC Bank", amount: 50000, tax: 18}`
3. ✅ Validate ledger exists
4. ✅ Validate amount is reasonable
5. ✅ Calculate total → ₹59,000
6. ✅ Generate XML → Valid Tally schema
7. ✅ Show preview → User sees transaction details
8. ✅ Get approval → User clicks "Approve"
9. ✅ Write to Tally → With rollback on failure
10. ✅ Respond → Transaction ID + confirmation

**All steps visible to user in real-time.**

---

## 🔧 Configuration

Add to `.env`:
```
# Agent Configuration
AGENT_MAX_RETRIES=3
AGENT_TIMEOUT_SECONDS=30
AGENT_MAX_TRANSACTION_AMOUNT=1000000
AGENT_REQUIRE_APPROVAL_ABOVE=100000
AGENT_DRY_RUN_MODE=false

# Gemini Configuration  
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TEMPERATURE=0.1
GEMINI_MAX_TOKENS=2048

# Tally Configuration
TALLY_URL=http://localhost:9000
TALLY_COMPANY=SHREE JI SALES
TALLY_EDU_MODE=true
TALLY_TIMEOUT=5
```

---

## 📝 Next Command

Tell me: **"continue"** and I'll build the LangGraph State Machine next!
