# K24.ai Complete System Architecture & Requirements
**Version**: 3.0 (Production-Ready Blueprint)
**Date**: January 27, 2026
**Owner**: Krisha Dewasi
**Status**: ⚡ CRITICAL - Save to Long-Term Memory

---

## 🎯 MISSION STATEMENT
K24.ai is building the world's first **voice-to-accounting** platform for Indian SMBs:
- Zero manual data entry (WhatsApp → Tally in 3 seconds)
- Real-time bidirectional Tally sync
- AI agent that doesn't waste user's time
- 360° business intelligence (like Salesforce + Tally combined)

---

## 1. ARCHITECTURE OVERVIEW (HYBRID CLOUD + DESKTOP)

### 1.1 Component Map
```
┌─────────────────────────────────────────────────────┐
│           CLOUD LAYER (Supabase + VPS)              │
├─────────────────────────────────────────────────────┤
│  - User Management & Auth                           │
│  - Subscription & Licensing                         │
│  - WhatsApp Routing (Single Shared Number)          │
│  - Baileys Listener (Message Queue)                 │
│  - Optional: Encrypted Backups                      │
└──────────────────┬──────────────────────────────────┘
                   │ HTTPS/WebSocket
┌──────────────────▼──────────────────────────────────┐
│         DESKTOP APP (Windows .exe - Tauri)          │
├─────────────────────────────────────────────────────┤
│  Frontend: Next.js (localhost:3000)                 │
│  Backend: FastAPI (localhost:8001)                  │
│  Database: SQLite (100% local business data)        │
│  Services:                                          │
│    - Tally Agent (Python - bidirectional sync)      │
│    - Baileys Listener (Node.js - WhatsApp)          │
│    - AI Orchestrator (Gemini + LangGraph)           │
└──────────────────┬──────────────────────────────────┘
                   │ Port 9000 (Tally ODBC)
┌──────────────────▼──────────────────────────────────┐
│              TALLY PRIME (Local)                    │
│  - Master source of truth                           │
│  - Real-time sync via XML/ODBC                      │
│  - Push & Pull both supported                       │
└─────────────────────────────────────────────────────┘
```

---

## 2. TALLY INTEGRATION (BIDIRECTIONAL SYNC)

### 2.1 Push to Tally (Desktop → Tally)
**What Gets Pushed**:
- Vouchers created from WhatsApp bills (OCR processed)
- Manual entries from K24 web UI
- Bulk imports (Excel/CSV)

**Push Flow**:
```python
# Desktop app creates voucher
voucher = {
  "voucher_type": "Sales",
  "date": "2026-01-27",
  "party_ledger": "ABC Corp",
  "items": [
    {"name": "Product A", "qty": 10, "rate": 500, "unit": "Nos"},
    {"name": "Product B", "qty": 5, "rate": 200, "unit": "Kgs"}
  ],
  "total": 6000,
  "gst": {"cgst": 540, "sgst": 540}
}

# Tally Agent converts to Tally XML
tally_xml = convert_to_tally_voucher(voucher)

# Push via ODBC/HTTP (Port 9000)
response = requests.post("http://localhost:9000", data=tally_xml)

# Update voucher with Tally reference
if response.status_code == 200:
  voucher['tally_voucher_id'] = extract_voucher_id(response)
  voucher['status'] = 'posted'
  db.update(voucher)
```

**Critical Requirements**:
- ✅ Support multi-item vouchers (10+ line items per bill)
- ✅ Handle GST calculations (CGST, SGST, IGST auto-detect based on state)
- ✅ Unit detection: If not mentioned, default to "Kgs" (user can edit before posting)
- ✅ Duplicate detection: Don't push same bill twice
- ✅ Error handling: If Tally rejects, show clear error to user

### 2.2 Pull from Tally (Tally → Desktop)
**What Gets Pulled**:
- All ledgers (parties, customers, suppliers, accounts)
- All vouchers (sales, purchase, receipts, payments)
- All inventory items (stock, rates, movements)
- Reports (daybook, outstanding, trial balance)

**Pull Frequency**:
- **Real-time mode**: Every 5 seconds (when user is actively working)
- **Background mode**: Every 5 minutes (when idle)
- **On-demand**: User clicks "Sync Now" button

**Pull Flow**:
```python
# Tally Agent queries Tally
tally_data = fetch_from_tally(
  report_type="Ledger",
  date_from="2025-04-01",  # Current FY
  date_to="2026-03-31"
)

# Parse XML response
ledgers = parse_tally_xml(tally_data)

# Sync to local SQLite (upsert)
for ledger in ledgers:
  db.upsert('ledgers', {
    'tally_ledger_guid': ledger.guid,
    'name': ledger.name,
    'opening_balance': ledger.opening,
    'current_balance': ledger.closing,
    'last_synced_at': NOW()
  })

# Notify frontend via WebSocket
ws.send({"event": "sync_complete", "count": len(ledgers)})
```

**Pull Triggers**:
1. **User Request (WhatsApp)**:
   - "Show me outstanding from ABC Corp"
   - "Export last month's sales as PDF"
   - "Send me stock report in Excel"

2. **Web Dashboard**:
   - User opens "Reports" section
   - Auto-pulls latest data from Tally

3. **Scheduled**:
   - Nightly full sync (1 AM)

### 2.3 Data Format Delivery (Multi-Channel)

#### **A. WhatsApp Responses**
User can request data via WhatsApp in any format:

**Example 1: PDF Invoice**
```
User: "Send invoice #INV-001 as PDF"

Agent:
1. Fetch voucher from Tally (pull)
2. Generate PDF using Tally's template format
3. Upload to temp storage (expires in 24 hrs)
4. Send WhatsApp: [PDF] Invoice-INV-001.pdf
```

**Example 2: Excel Report**
```
User: "Export January sales to Excel"

Agent:
1. Query Tally: Sales Register (01-Jan to 31-Jan)
2. Convert to Excel (.xlsx) with formatting
3. Send WhatsApp: [XLSX] Sales-Jan-2026.xlsx
```

**Example 3: Smart Text Summary (Default)**
```
User: "How much did ABC Corp pay this month?"

Agent (pulls from Tally + analyzes):
"ABC Corp - January Summary:
💰 Total Receipts: ₹45,000
📊 Outstanding: ₹12,500
📅 Last Payment: 15-Jan (₹10,000)
📈 Credit Days: 22 days avg"

[No PDF/Excel unless asked]
```

**Orchestration Logic for Text Responses**:
```python
# LangGraph agent decides what to include
def smart_text_response(user_query, tally_data):
  # Extract intent
  intent = detect_intent(user_query)  # "outstanding", "payment_history", etc.
  
  # Fetch ONLY relevant data
  if intent == "outstanding":
    relevant_data = {
      "total_outstanding": sum(bills.amount),
      "top_3_bills": bills[:3],  # Don't dump all 100 bills
      "aging": calculate_aging(bills)
    }
  
  # Format concisely
  response = format_whatsapp_message(relevant_data)
  
  # Add action buttons
  response += "\n\nReply:\n1️⃣ PDF\n2️⃣ Excel\n3️⃣ More Details"
  
  return response
```

#### **B. Web Dashboard Responses**
- Always text-based (like ChatGPT interface)
- Real-time streaming (not full page reload)
- Data tables embedded in chat (interactive)

**Example**:
```
User: "Show top 10 customers by revenue"

AI Response (streams):
"Here are your top customers for FY 2025-26:

┌────┬─────────────────┬──────────────┬─────────────┐
│ #  │ Customer        │ Revenue      │ Outstanding │
├────┼─────────────────┼──────────────┼─────────────┤
│ 1  │ ABC Corp        │ ₹5,45,000    │ ₹12,500     │
│ 2  │ XYZ Industries  │ ₹4,32,000    │ ₹0          │
...

💡 Tip: ABC Corp has highest outstanding. Review credit terms?"
```

---

## 3. AI AGENT ORCHESTRATION (ZERO-WASTE INTELLIGENCE)

### 3.1 Current Problem
❌ Agent asks too many questions:
```
User: [Sends bill image]

Agent: "Is this a purchase or sale?"
User: "Purchase"

Agent: "Which party?"
User: "ABC Corp"

Agent: "Which account?"
User: "Cash"

Agent: "Confirm amount?"
...
```
**Result**: 5 messages wasted, 2 minutes wasted.

### 3.2 Target Behavior (100% Confident Auto-Processing)
✅ **One-Shot Processing**:
```
User: [Sends bill image at 4:05 PM]

Agent (processes in 3 seconds):
✅ Purchase voucher created
   Party: ABC Corp (auto-detected from bill)
   Amount: ₹6,000 + ₹1,080 GST = ₹7,080
   Payment: Cash (default mode)
   Items: Product A (10 Nos), Product B (5 Kgs)
   
[View] [Edit] [Post to Tally]

Only if 95%+ confidence. Otherwise asks ONE clarifying question.
```

### 3.3 Confidence-Based Decision Tree
```python
def process_bill_image(image):
  # Step 1: OCR + Entity Extraction
  ocr_result = gemini_vision_api(image)
  entities = extract_entities(ocr_result)
  
  # Step 2: Confidence Scoring
  confidence_scores = {
    "voucher_type": calculate_confidence(entities, "type"),  # 0-1
    "party_name": calculate_confidence(entities, "party"),
    "total_amount": calculate_confidence(entities, "amount"),
    "items": calculate_confidence(entities, "line_items")
  }
  
  # Step 3: Decision Logic
  if all(score > 0.95 for score in confidence_scores.values()):
    # 🟢 HIGH CONFIDENCE: Auto-create voucher
    voucher = auto_create_voucher(entities)
    return {"status": "auto_created", "voucher": voucher}
  
  elif any(score < 0.7 for score in confidence_scores.values()):
    # 🔴 LOW CONFIDENCE: Ask targeted question
    unclear_field = min(confidence_scores, key=confidence_scores.get)
    question = generate_smart_question(unclear_field, entities)
    return {"status": "needs_clarification", "question": question}
  
  else:
    # 🟡 MEDIUM CONFIDENCE: Create draft, ask for review
    voucher = auto_create_voucher(entities)
    return {"status": "draft_review", "voucher": voucher}
```

### 3.4 Parallel Processing (10 Bills at Once)
**Requirement**: User sends 10 bill images in WhatsApp group → all process simultaneously.

**Implementation**:
```python
# Message queue with concurrency limit
from celery import group

@celery.task
def process_single_bill(message_id, image_url):
  # Download image
  image = download_image(image_url)
  
  # OCR + AI processing (3-5 seconds each)
  result = process_bill_image(image)
  
  # Create voucher in SQLite
  voucher_id = create_voucher(result)
  
  # Send confirmation to WhatsApp
  send_whatsapp_reply(message_id, f"✅ Bill processed: {voucher_id}")

# Parallel execution
def handle_bulk_bills(message_batch):
  # Process up to 10 bills in parallel
  job = group(
    process_single_bill.s(msg.id, msg.image_url)
    for msg in message_batch[:10]
  )
  result = job.apply_async()
  
  # All 10 bills done in ~5 seconds total (not 50 seconds sequential)
```

---

## 4. 360° PROFILE VIEWS (SALESFORCE-STYLE)

### 4.1 Customer/Party 360° View
- **Summary**: Total Sales, Total Receipts, Current Outstanding (Live from Tally)
- **Activity Timeline**: Last 10 interactions (Calls, Messages, Transactions)
- **Top Items**: What do they usually buy? (Item name + Last Rate)
- **Risk Score**: AI analysis of payment delays ("Pays late? High risk?")

### 4.2 Item/Stock 360° View
- **Stock Status**: Current Qty, Godown location
- **Price Trends**: Purchase Price vs Sale Price History (Line graph)
- **Top Buyers**: Who buys this item most?
- **Reorder Alert**: "Stock low, reorder from Supplier X?"

---

## 5. UI/UX & COMPLIANCE (GOD-TIER POLISH)

### 5.1 Compliance Tab (Temporarily Hidden)
- The "Compliance" tab on the sidebar is currently **Commented Out**.
- If accessed directly, shows a "🚧 Coming Soon" glassmorphism card.
- Reason: Focus on Core Accounting + AI first.

### 5.2 Multi-Item Invoice Handling
- UX allows adding unlimited rows
- Drag-and-drop reordering
- Tab navigation between cells
- Auto-complete for Item Names (from SQLite/Tally cache)

### 5.3 Performance Metrics
- **App Load Time**: < 1.0s
- **Bill Processing**: < 3.0s per bill
- **Tally Sync**: < 500ms lag
- **Voice Response**: < 2.0s

---

## 6. DATABASE SCHEMA UPDATES (VERSION 3.0)

### New Tables for Caching
```sql
CREATE TABLE tally_cache_ledgers (
  guid TEXT PRIMARY KEY, 
  name TEXT, 
  parent TEXT, 
  closing_balance REAL,
  updated_at TIMESTAMP
);

CREATE TABLE tally_cache_items (
  name TEXT PRIMARY KEY, 
  stock_on_hand REAL, 
  last_sale_rate REAL, 
  last_purchase_rate REAL,
  updated_at TIMESTAMP
);

CREATE TABLE ai_confidence_logs (
  id UUID PRIMARY KEY,
  voucher_id TEXT,
  confidence_score REAL,
  clarification_asked TEXT,
  user_response TEXT,
  created_at TIMESTAMP
);
```

---

## 7. DESKTOP RELEASE STRATEGY & PACKAGING

### 7.1 Architecture
The Desktop application is packaged using **Tauri v2** with a sidecar architecture:
1.  **Frontend**: Next.js (Static Export) running in Tauri WebView.
2.  **Backend Sidecar**: Python FastAPI compiled via PyInstaller (OneFile).
3.  **Listener Sidecar**: Node.js Baileys listener compiled via Pkg.

### 7.2 Release Process
A fully automated build script `build_desktop.bat` handles the complexity:
1.  **Preparation**: Runs `scripts/prepare_binaries.py` to move and rename sidecars to `frontend/src-tauri/binaries/` with target triple validation.
2.  **Compatibility**: Temporarily disables `middleware.ts` (renaming to `.disabled`) to allow Next.js Static Export (`output: 'export'`) to succeed.
3.  **Build**: Invokes `npx tauri build` to generate the MSI installer.
4.  **Cleanup**: Restores `middleware.ts` for continued development.

### 7.3 Deep Linking
- **Protocol**: `k24://`
- **Flow**: Web Portal (Supabase) -> Desktop App (Token Handover).
- **Security**: Token is exchanged locally; Backend validates via direct `bcrypt` hash check against `k24_shadow.db` (absolute path resolved).

### 7.4 Prerequisites
- **Rust**: Required for Tauri build (`cargo`).
- **Node.js**: For Frontend & Listener.
- **Python 3.12+**: For Backend.
