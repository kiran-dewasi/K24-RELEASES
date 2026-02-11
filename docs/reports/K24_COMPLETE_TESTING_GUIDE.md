# K24 System - Complete Testing Guide 🧪

**Your Side-by-Side Testing Companion**  
**Version**: 1.0 | **Last Updated**: 2025-11-28

---

## 📖 HOW TO USE THIS GUIDE

Keep this document open in one window while testing the K24 system in your browser. Follow each section systematically to verify every feature.

**Prerequisites**:
- ✅ Tally Prime is running on `localhost:9000`
- ✅ Backend is running: `uvicorn backend.api:app --reload --port 8001`
- ✅ Frontend is running: `npm run dev` (usually on `http://localhost:3000`)

---

## 🎯 SYSTEM ARCHITECTURE OVERVIEW

### Technology Stack
```
Frontend: Next.js 14 (TypeScript) → http://localhost:3000
Backend:  FastAPI (Python) → http://localhost:8001
Database: SQLite (Shadow DB in backend/k24.db)
AI:       Google Gemini (Natural Language Processing)
ERP:      Tally Prime (via XML HTTP API on port 9000)
```

### Data Flow
```
User Input → Frontend → Backend API → Tally/Database
                      ↓
                  AI/Gemini Processing
                      ↓
             Response → Frontend
```

---

## 🗺️ COMPLETE FEATURE MAP

### **Pages and Routes**

| **Route** | **Purpose** | **Status** |
|-----------|------------|-----------|
| `/` | Dashboard (Home) | ✅ Production |
| `/chat` | Full-page AI Chat with KITTU | ✅ Production |
| `/daybook` | View all vouchers (transactions) | ✅ Production |
| `/contacts/[name]` | Transaction history for specific party | ✅ Production |
| `/vouchers/new/receipt` | Create Receipt Voucher | ✅ Production |
| `/vouchers/new/payment` | Create Payment Voucher | ✅ Production |
| `/vouchers/new/sales` | Create Sales Invoice | ✅ Production |
| `/reports/outstanding` | Outstanding Receivables Report | ✅ Production |
| `/reports/balance-sheet` | Balance Sheet | ✅ Production |
| `/reports/profit-loss` | Profit & Loss Statement | ✅ Production |
| `/reports/trial-balance` | Trial Balance | ✅ Production |
| `/reports/cash-book` | Cash Book | ✅ Production |
| `/reports/bank-book` | Bank Book | ✅ Production |
| `/search` | Global Search | ✅ Production |
| `/operations/gstin-update` | Update Party GSTIN | ✅ Production |

### **Backend API Endpoints**

| **Endpoint** | **Method** | **Purpose** |
|--------------|------------|-------------|
| `/chat` | POST | AI Assistant (processes natural language) |
| `/vouchers` | GET | Fetch all vouchers from database |
| `/vouchers/receipt` | POST | Create Receipt voucher |
| `/vouchers/payment` | POST | Create Payment voucher |
| `/vouchers/sales` | POST | Create Sales Invoice |
| `/ledgers/search?query=X` | GET | Autocomplete party names from Tally |
| `/ledgers/{name}/vouchers` | GET | Fetch transactions for specific ledger |
| `/reports/outstanding` | GET | Outstanding bills |
| `/reports/balance-sheet` | GET | Balance Sheet from Tally |
| `/reports/profit-loss` | GET | P&L from Tally |
| `/reports/trial-balance` | GET | Trial Balance from Tally |
| `/reports/cash-book` | GET | Cash Book from Tally |
| `/audit/run` | GET | Run compliance audit (Section 44AB) |

**Authentication**: All API endpoints require header `x-api-key: k24-secret-key-123`

---

## 🧪 SECTION 1: DASHBOARD TESTING

### **What to Test**
The homepage at `http://localhost:3000`

### **Features to Verify**

1. **Magic Input (AI Chat)**
   - [ ] Large input box is visible and focused on page load
   - [ ] You can type a query
   - [ ] Pressing Enter submits the query
   - [ ] Success: Input clears automatically after submission ✅ (NEW!)
   - [ ] Loading state shows while processing

2. **Quick Stats Cards**
   - [ ] 4 cards visible: Today's Sales, Outstanding, Bank Balance, etc.
   - [ ] Numbers are loading from Tally OR showing placeholder

3. **Navigation**
   - [ ] Sidebar has links to Daybook, Reports, Chat, etc.
   - [ ] Clicking each link navigates correctly

4. **Floating AI Button**
   - [ ] Bottom-right corner has a chat icon
   - [ ] Clicking opens AI chat interface

### **Test Commands** (Type in Magic Input)

| Command | Expected Result |
|---------|----------------|
| `"Receipt from Sharma for 5000"` | Navigates to `/vouchers/new/receipt` with pre-filled form |
| `"Show daybook"` | Opens `/daybook` |
| `"What's my balance?"` | Shows text response with balance info |
| `"Show outstanding"` | Opens `/reports/outstanding` |

### **Expected Behavior**
- All navigation is smooth (no crashes)
- AI responses appear within 2-3 seconds
- Input field clears after submission

---

## 🧪 SECTION 2: CHAT INTERFACE TESTING

### **Page**: `/chat`

### **Features to Verify**

1. **Interface Elements**
   - [ ] Greeting shows "Good evening, Kiran" (or appropriate time of day)
   - [ ] Large textarea input (not single-line)
   - [ ] "Send Message" button on bottom-right of input
   - [ ] Input auto-focuses on page load
   - [ ] ✅ Input clears after sending message (NEW!)

2. **Suggestion Buttons**
   - [ ] 4 suggestion buttons below input:
     - "Show me outstanding receivables"
     - "Create a sales invoice for ABC Corp"
     - "What's my cash balance today?"
     - "Run a compliance audit check"
   - [ ] Clicking a suggestion fills the input
   - [ ] You can then edit and send

3. **Message Sending**
   - [ ] Press Enter to send (without Shift)
   - [ ] Shift+Enter creates new line
   - [ ] "Send Message" button works
   - [ ] Loading state shows while processing

4. **Response Display**
   - [ ] AI response appears in a card below input
   - [ ] Card has "KITTU" header with sparkle icon
   - [ ] Response text is formatted nicely
   - [ ] "Clear" button dismisses response

### **Test Scenarios**

**Test 1: Simple Text Response**
```
Type: "What is K24?"
Expected: Text response in a card explaining the system
```

**Test 2: Navigation Command**
```
Type: "Open balance sheet"
Expected: Navigates to /reports/balance-sheet after 1-2 seconds
```

**Test 3: Draft Voucher**
```
Type: "Sale to Sharma"
Expected: Draft card appears with party name filled
```

**Test 4: Follow-up Questions**
```
Type: "Receipt from ABC"
Expected: KITTU asks "How much did you receive?"
```

---

## 🧪 SECTION 3: DAY BOOK TESTING

### **Page**: `/daybook`

### **Features to Verify**

1. **Summary Cards (Top Section)**
   - [ ] 4 cards showing counts:
     - Receipts (green)
     - Payments (red)
     - Sales (green)
     - Purchase (red)
   - [ ] Each card shows a number
   - [ ] Cards are clickable

2. **Filtering**
   - [ ] Click "Receipts" card → List shows only Receipt vouchers
   - [ ] Click "Payments" card → List shows only Payment vouchers
   - [ ] "Clear Filter" button appears when filtered
   - [ ] Click "Clear Filter" → Shows all vouchers again

3. **Voucher List**
   - [ ] Shows vouchers in reverse chronological order (newest first)
   - [ ] Each voucher has:
     - Icon (based on type)
     - Party name
     - Amount (green for income, red for expense)
     - Date
     - Narration (if available)
   - [ ] Hover effect on voucher rows

4. **Quick Actions**
   - [ ] "New Receipt" button (green) in top-right
   - [ ] "New Payment" button (red) in top-right
   - [ ] Clicking opens respective form

5. **Floating AI**
   - [ ] Bottom-right chat icon
   - [ ] Context-aware: "What's the total?" should calculate daybook total

### **Test Scenario**

**Test Complete Flow**:
1. Open `/daybook`
2. Check: See all vouchers
3. Click "Receipts" card
4. Check: Only receipts visible
5. Click "Clear Filter"
6. Check: All vouchers back
7. Click "New Receipt"
8. Check: Navigates to `/vouchers/new/receipt`

---

## 🧪 SECTION 4: RECEIPT VOUCHER TESTING

### **Page**: `/vouchers/new/receipt`

### **Features to Verify**

1. **Form Fields**
   - [ ] Party Name (autocomplete input)
   - [ ] Amount (number input)
   - [ ] Date (date picker, defaults to today)
   - [ ] Mode of Receipt (dropdown: Cash, Bank, UPI, etc.)
   - [ ] Deposit To (defaults to "Cash")
   - [ ] Narration (textarea, optional)

2. **Autocomplete (Critical Feature)**
   - [ ] Start typing a party name (e.g., "Shar")
   - [ ] Dropdown appears with matches from Tally
   - [ ] Matches appear within 500ms
   - [ ] Click a match to select
   - [ ] Keyboard navigation: Arrow keys work, Enter selects
   - [ ] No matches: Shows "No parties found"

3. **Validation**
   - [ ] Party Name required (error if empty)
   - [ ] Amount must be > 0 (error if 0 or negative)
   - [ ] Date cannot be future (should warn)

4. **Pre-filled from AI**
   - [ ] If you came from chat saying "Receipt from ABC for 5000":
     - Party = "ABC"
     - Amount = 5000
   - [ ] You can still edit before submitting

5. **Submission**
   - [ ] Click "Create Receipt" button
   - [ ] Button shows loading spinner
   - [ ] Success: Toast notification appears
   - [ ] Success: Redirects to `/daybook` or shows success message
   - [ ] Error: Error message displays

### **Test Scenarios**

**Test 1: Manual Entry (Full Flow)**
```
1. Go to /vouchers/new/receipt
2. Type "Sharma" in Party Name
3. Select "Sharma Traders" from autocomplete
4. Enter Amount: 10000
5. Select Mode: "Cash"
6. Enter Narration: "Payment received for invoice #123"
7. Click "Create Receipt"
8. Expected: Success message → Voucher created in Tally
9. Check Tally: Receipt voucher exists
10. Check /daybook: New voucher appears
```

**Test 2: Voice Command Pre-fill**
```
1. Go to /chat
2. Say: "Receipt from Sharma for 7500"
3. Expected: Navigates to /vouchers/new/receipt
4. Check: Party = "Sharma", Amount = 7500
5. Autocomplete suggests "Sharma Traders"
6. Select and submit
```

**Test 3: Autocomplete Edge Cases**
```
Test 3a: Exact Match
- Type: "Cash" → Should show "Cash" ledger

Test 3b: Partial Match
- Type: "Shar" → Shows all ledgers starting with "Shar"

Test 3c: No Match
- Type: "XYZABC123" → Shows "No parties found"
```

---

## 🧪 SECTION 5: PAYMENT VOUCHER TESTING

### **Page**: `/vouchers/new/payment`

### **Features to Verify**

Similar to Receipt, but:
- [ ] Party Name autocomplete
- [ ] Amount input
- [ ] Date picker
- [ ] Payment Mode (Cash, Bank, UPI, Cheque)
- [ ] Pay From (defaults to "Cash")
- [ ] Narration
- [ ] Submits to `/vouchers/payment` endpoint

### **Test Scenario**

```
1. Go to /daybook
2. Click "New Payment" button
3. Enter Party: "ABC Suppliers"
4. Enter Amount: 15000
5. Select Mode: "Bank Transfer"
6. Enter Narration: "Payment for raw materials"
7. Click "Create Payment"
8. Expected: Success → Voucher in Tally and daybook
```

---

## 🧪 SECTION 6: SALES INVOICE TESTING

### **Page**: `/vouchers/new/sales`

### **Features to Verify**

1. **Invoice Header**
   - [ ] Party Name (autocomplete)
   - [ ] Invoice Number (auto-generated or manual)
   - [ ] Invoice Date (date picker)

2. **Line Items**
   - [ ] "Add Item" button
   - [ ] Each line has:
     - Description (text or autocomplete from stock items)
     - Quantity (number)
     - Rate (number)
     - Amount (auto-calculated)
   - [ ] "Remove" button for each line
   - [ ] Can add multiple items

3. **Calculation Section**
   - [ ] Subtotal (sum of all line items)
   - [ ] Discount % (optional)
   - [ ] Discount Amount (auto-calculated)
   - [ ] GST Rate (dropdown: 0%, 5%, 12%, 18%, 28%)
   - [ ] GST Amount (auto-calculated)
   - [ ] Grand Total (bold, highlighted)

4. **GST Intelligence**
   - [ ] If party's state = your state → Shows CGST + SGST
   - [ ] If party's state ≠ your state → Shows IGST
   - [ ] Auto-detects based on GSTIN

5. **Submission**
   - [ ] "Create Invoice" button
   - [ ] Sends to `/vouchers/sales`
   - [ ] Success: Invoice created in Tally
   - [ ] PDF generation (if implemented)

### **Test Scenario**

**Complete Sales Invoice Flow**:
```
1. Go to /vouchers/new/sales
2. Party Name: "ABC Corp"
3. Invoice Date: Today
4. Add Item 1:
   - Description: "Product A"
   - Quantity: 10
   - Rate: 500
   - Amount: 5000 (auto-calculated)
5. Add Item 2:
   - Description: "Product B"
   - Quantity: 5
   - Rate: 200
   - Amount: 1000 (auto-calculated)
6. Check Subtotal: ₹6,000
7. Apply Discount: 10%
8. Check Discount Amount: ₹600
9. Check Taxable Amount: ₹5,400
10. Select GST: 18%
11. Check GST Amount: ₹972
12. Check Grand Total: ₹6,372
13. Click "Create Invoice"
14. Expected: Success message
15. Check Tally: Sales voucher exists with all items
16. Check /daybook: New sales entry appears
```

---

## 🧪 SECTION 7: CONTACT VIEW TESTING

### **Page**: `/contacts/[name]` (e.g., `/contacts/Sharma%20Traders`)

### **Features to Verify**

1. **Header Section**
   - [ ] Party name displayed prominently
   - [ ] Total transaction value
   - [ ] Number of transactions

2. **Transaction List**
   - [ ] All vouchers for this party
   - [ ] Sorted by date (newest first)
   - [ ] Each voucher shows:
     - Date
     - Type (Receipt, Payment, Sales, Purchase)
     - Amount
     - Narration
   - [ ] Color coding (green for income, red for expense)

3. **Context-Aware AI**
   - [ ] Floating chat icon
   - [ ] Knows the party you're viewing
   - [ ] Questions like "What's the total?" should answer for THIS party

### **Test Scenario**

**Test via Voice Command**:
```
1. Go to /chat
2. Type: "Show me Sharma's history"
3. Expected: Navigates to /contacts/Sharma%20Traders
4. Check: All transactions for Sharma visible
5. Type in floating AI: "What's the biggest transaction?"
6. Expected: AI responds with largest amount
```

**Test via Direct URL**:
```
1. Go to /contacts/Cash
2. Expected: All cash transactions visible
3. Check: Receipts and payments both show
```

---

## 🧪 SECTION 8: OUTSTANDING REPORT TESTING

### **Page**: `/reports/outstanding`

### **Features to Verify**

1. **Report Layout**
   - [ ] Title: "Outstanding Receivables"
   - [ ] Date range or "As of Today"
   - [ ] Table with columns:
     - Party Name
     - Bill Number
     - Bill Date
     - Due Date
     - Amount
     - Days Overdue (if applicable)

2. **Data Accuracy**
   - [ ] Shows only unpaid invoices
   - [ ] Amounts match Tally's Outstanding Report
   - [ ] Sorted by due date or party name

3. **Totals**
   - [ ] Total outstanding at bottom (highlighted)
   - [ ] Summary by aging (if implemented):
     - Current (0-30 days)
     - 30-60 days
     - 60-90 days
     - 90+ days

4. **Context-Aware AI**
   - [ ] Can ask "Who owes the most?"
   - [ ] Can ask "What's overdue?"

### **Test Scenario**

```
1. Open /reports/outstanding
2. Check: Bills listed
3. Verify: Total matches Tally (open Tally → Display → Outstanding)
4. Click floating AI
5. Ask: "Who owes the most?"
6. Expected: AI identifies the party with highest outstanding
```

---

## 🧪 SECTION 9: BALANCE SHEET TESTING

### **Page**: `/reports/balance-sheet`

### **Features to Verify**

1. **Report Structure**
   - [ ] Two-column layout:
     - Left: Liabilities
     - Right: Assets
   - [ ] Each side shows groups:
     - Capital Accounts
     - Current Liabilities
     - Fixed Assets
     - Current Assets
     - etc.

2. **Data Integrity**
   - [ ] Numbers match Tally exactly
   - [ ] Both sides balance (total assets = total liabilities)

3. **Date Selector**
   - [ ] Can select "As of Date"
   - [ ] Report updates when date changes

4. **Context-Aware AI**
   - [ ] Can ask "What's the total assets?"
   - [ ] Can ask "What's my net worth?"

### **Test Scenario**

```
1. Open /reports/balance-sheet
2. Check: Report loads from Tally
3. Verify: Assets total = Liabilities total
4. Compare with Tally (Gateway → Balance Sheet)
5. Ask AI: "What's my capital?"
6. Expected: AI reads from visible balance sheet
```

---

## 🧪 SECTION 10: AI/NATURAL LANGUAGE TESTING

### **Comprehensive Voice Command Tests**

| **Command** | **Expected Result** | **Test Status** |
|-------------|---------------------|----------------|
| `"Receipt from Sharma for 5000"` | Opens `/vouchers/new/receipt` pre-filled | [ ] |
| `"Payment to ABC for 8000"` | Opens `/vouchers/new/payment` pre-filled | [ ] |
| `"Sale to XYZ Corp"` | Shows draft card or opens sales form | [ ] |
| `"Show daybook"` | Opens `/daybook` | [ ] |
| `"Show balance sheet"` | Opens `/reports/balance-sheet` | [ ] |
| `"Show outstanding"` | Opens `/reports/outstanding` | [ ] |
| `"What's my cash balance?"` | Text response with current cash balance | [ ] |
| `"Show me Sharma's history"` | Opens `/contacts/Sharma` | [ ] |
| `"Who are my top customers?"` | Text response with analysis | [ ] |
| `"Run audit check"` | Runs compliance audit, shows results | [ ] |

### **Context-Awareness Tests**

**Test 1: Dashboard Context**
```
Location: /
Ask: "What's the balance?"
Expected: Shows overall business balance
```

**Test 2: Cash Book Context**
```
Location: /reports/cash-book
Ask: "What's the balance?"
Expected: Shows cash ledger balance (not total)
```

**Test 3: Contact Context**
```
Location: /contacts/Sharma
Ask: "What did I sell to them?"
Expected: Summarizes sales transactions to Sharma
```

---

## 🧪 SECTION 11: AUTOCOMPLETE SYSTEM TESTING

### **Critical Feature**: Live Party Lookup

### **How It Works**
1. User types in Party Name field
2. After 300ms debounce, frontend sends: `GET /ledgers/search?query=<text>`
3. Backend calls `tally.lookup_ledger(query)`
4. Tally returns matching ledger names
5. Frontend shows dropdown with matches

### **Test Matrix**

| **Input** | **Expected Matches** | **Notes** |
|-----------|---------------------|-----------|
| `"Cash"` | Cash | Exact match |
| `"Shar"` | Sharma, Sharma Traders, Sharif Enterprise | Partial match |
| `"ABC"` | ABC Corp, ABC Traders, ABC Suppliers | Multiple matches |
| `"sales"` | Sales, Sales Return | Case-insensitive |
| `"XYZ123"` | (empty) | No match → "No parties found" |

### **Performance Tests**
- [ ] Response time < 500ms
- [ ] Works with Tally closed → Should show error or empty
- [ ] Works with large ledger list (1000+ ledgers)
- [ ] No lag while typing (debounced correctly)

### **Edge Cases**
- [ ] Special characters: "M/s ABC & Co."
- [ ] Numbers: "123 Enterprises"
- [ ] Spaces: "  Leading spaces  "
- [ ] Unicode: "नमस्ते Traders"

---

## 🧪 SECTION 12: TALLY SYNC TESTING

### **Two-Way Sync Verification**

### **Test 1: K24 → Tally (Write)**
```
1. Create a Receipt in K24
2. Open Tally
3. Go to: Display → Daybook
4. Check: Receipt voucher exists
5. Verify: All fields match (party, amount, date, narration)
```

### **Test 2: Tally → K24 (Read)**
```
1. Create a Payment voucher manually in Tally
2. Go to K24 /daybook
3. Refresh the page
4. Check: New payment appears in list
5. Verify: All details correct
```

### **Test 3: Ledger Autocomplete**
```
1. Add a new ledger "Test Party 123" in Tally
2. Go to K24 /vouchers/new/receipt
3. Type "Test" in Party Name
4. Check: "Test Party 123" appears in suggestions
```

### **Test 4: Outstanding Sync**
```
1. Mark an invoice as paid in Tally
2. Go to K24 /reports/outstanding
3. Refresh
4. Check: Invoice no longer shows
```

### **Error Scenarios**
- [ ] Tally is closed → K24 shows error message
- [ ] Tally wrong company → K24 shows "Company not found"
- [ ] Network error → K24 shows "Connection failed"

---

## 🧪 SECTION 13: DATABASE TESTING

### **Shadow Database (SQLite)**

The system maintains a **local copy** of vouchers in `backend/k24.db`

### **What to Verify**

1. **Voucher Storage**
   - [ ] Every voucher created in K24 is saved to database
   - [ ] Even if Tally sync fails, voucher is in database
   - [ ] Database has columns: id, guid, voucher_number, date, voucher_type, party_name, amount, narration, sync_status

2. **Sync Status Tracking**
   - [ ] Successful Tally sync → `sync_status = "SYNCED"`
   - [ ] Failed Tally sync → `sync_status = "ERROR"`
   - [ ] Manual creation → `sync_status = "PENDING"`

3. **Fast Retrieval**
   - [ ] `/vouchers` endpoint reads from database (not Tally)
   - [ ] Response time < 100ms even with 10,000 vouchers

### **Testing Steps**

**Test Database Persistence**:
```
1. Create a receipt voucher
2. Stop the backend (Ctrl+C)
3. Restart backend
4. Go to /daybook
5. Check: Previously created voucher still appears
```

**Test Offline Mode**:
```
1. Close Tally
2. Create a receipt in K24
3. Expected: Voucher saves to database
4. Check database: sync_status = "ERROR" or "PENDING"
5. Open Tally
6. TODO: Background sync should retry (if implemented)
```

---

## 🧪 SECTION 14: UI/UX TESTING

### **Recent  Improvements** (✅ Implemented)

1. **Input Auto-Clear**
   - [ ] After sending chat message, input field clears
   - [ ] After sending dashboard query, input field clears
   - [ ] Works on both `/chat` and `/` pages

### **General UX Checklist**

1. **Loading States**
   - [ ] All buttons show spinner when processing
   - [ ] Text changes to "Creating..." or "Loading..."

2. **Error Handling**
   - [ ] Error messages are user-friendly (not raw API errors)
   - [ ] Errors show in toast notifications (top-right)
   - [ ] Errors disappear after 5 seconds

3. **Success Feedback**
   - [ ] Green checkmark or toast on success
   - [ ] Message shows what was created (e.g., "Receipt for ₹5000 created")

4. **Responsive Design**
   - [ ] Works on desktop (1920x1080)
   - [ ] Works on laptop (1366x768)
   - [ ] Works on tablet (iPad)
   - [ ] Mobile layout (if implemented)

5. **Keyboard Navigation**
   - [ ] Tab key moves through form fields
   - [ ] Enter submits form
   - [ ] Escape closes modals
   - [ ] Arrow keys navigate autocomplete

6. **Visual Polish**
   - [ ] Icons next to voucher types
   - [ ] Color coding (green for income, red for expense)
   - [ ] Hover effects on buttons and cards
   - [ ] Smooth transitions

---

## 🧪 SECTION 15: PERFORMANCE TESTING

### **Speed Benchmarks**

| **Operation** | **Target Time** | **Actual** | **Pass/Fail** |
|---------------|----------------|-----------|---------------|
| Page load (/) | < 1s | | |
| API response (/vouchers) | < 500ms | | |
| Autocomplete search | < 300ms | | |
| Create voucher | < 2s | | |
| Tally sync | < 3s | | |
| Balance sheet load | < 5s | | |

### **Load Testing**

1. **Large Data Sets**
   - [ ] 1,000 vouchers in daybook → Loads in < 2s
   - [ ] 10,000 ledgers → Autocomplete still responsive
   - [ ] 500 outstanding bills → Report loads in < 3s

2. **Concurrent Users**
   - [ ] Not applicable (single-user system)

---

## 🧪 SECTION 16: ERROR RECOVERY TESTING

### **Failure Scenarios**

**Test 1: Backend Crash**
```
1. Stop backend (Ctrl+C in terminal)
2. Try to create a voucher
3. Expected: Error message "Backend is offline"
4. Start backend
5. Retry → Should work
```

**Test 2: Tally Crash**
```
1. Close Tally
2. Try to create a voucher
3. Expected: Voucher saves to K24 database
4. Error message: "Tally sync failed, will retry later"
5. Open Tally
6. TODO: Auto-retry (if implemented)
```

**Test 3: Network Error**
```
1. Disconnect internet (if Tally is remote)
2. Try to fetch balance sheet
3. Expected: "Network error" message
4. Reconnect
5. Retry → Should work
```

**Test 4: Invalid Data**
```
1. Try to create receipt with amount = -100
2. Expected: Validation error "Amount must be positive"
3. Try to create receipt with party = ""
4. Expected: "Party name is required"
```

---

## 🧪 SECTION 17: SECURITY TESTING

### **API Key Validation**

1. **Test Without API Key**
```bash
# In terminal or Postman
curl http://localhost:8001/vouchers

Expected: 403 Forbidden
```

2. **Test With Wrong API Key**
```bash
curl -H "x-api-key: wrong-key" http://localhost:8001/vouchers

Expected: 403 Forbidden
```

3. **Test With Correct API Key**
```bash
curl -H "x-api-key: k24-secret-key-123" http://localhost:8001/vouchers

Expected: 200 OK with data
```

### **CORS Testing**
- [ ] Frontend at localhost:3000 can call backend at localhost:8001
- [ ] No CORS errors in browser console

---

## 🧪 SECTION 18: GSTIN & TAX TESTING

### **GST Intelligence**

**Test 1: GSTIN Validation**
```
1. Go to /operations/gstin-update
2. Enter Party Name: "ABC Corp"
3. Enter GSTIN: "27AAAAA1234A1Z5" (Maharashtra)
4. Click Submit
5. Expected: GSTIN validated and saved to Tally
```

**Test 2: GST Calculation (Sales Invoice)**
```
Scenario A: Intra-State (Same State)
- Your State: Maharashtra (27)
- Party GSTIN: 27AAAAA1234A1Z5 (Maharashtra)
- Expected: CGST + SGST (e.g., 9% + 9% = 18%)

Scenario B: Inter-State (Different State)
- Your State: Maharashtra (27)
- Party GSTIN: 29AAAAA1234A1Z5 (Karnataka)
- Expected: IGST (18%)
```

**Test 3: Compliance Audit**
```
1. Go to /chat
2. Type: "Run audit check"
3. Expected: Compliance report shows:
   - Missing GSTINs
   - Invalid GSTINs
   - Tax calculation errors
   - Section 44AB compliance
```

---

## 🧪 SECTION 19: REGRESSION TESTING CHECKLIST

After any code changes, verify these critical flows still work:

### **Core Flow 1: Create Receipt**
- [ ] Voice: "Receipt from Sharma for 5000" → Success
- [ ] Manual: Go to form → Fill → Submit → Success
- [ ] Verify in Tally
- [ ] Verify in /daybook

### **Core Flow 2: View Daybook**
- [ ] /daybook loads all vouchers
- [ ] Filtering works (click Receipt card)
- [ ] Voucher details correct

### **Core Flow 3: Autocomplete**
- [ ] Type "Shar" → See suggestions
- [ ] Select → Party fills
- [ ] Works on Receipt, Payment, Sales forms

### **Core Flow 4: Reports**
- [ ] Balance Sheet loads
- [ ] Outstanding Report loads
- [ ] Cash Book loads

### **Core Flow 5: AI Chat**
- [ ] Dashboard AI accepts queries
- [ ] /chat page works
- [ ] Input clears after submission ✅

---

## 🐛 KNOWN ISSUES & LIMITATIONS

| **Issue** | **Severity** | **Workaround** |
|-----------|-------------|---------------|
| Tally must be running on port 9000 | Critical | Start Tally before K24 |
| Large reports (10,000+ entries) may be slow | Medium | Pagination needed |
| No Edit/Delete vouchers in UI | Low | Edit in Tally directly |
| No PDF generation for invoices | Low | Use Tally's print feature |
| Single-user only (no multi-tenancy) | Medium | Use separate Tally companies |

---

## 📊 TESTING SCORECARD

Use this to track your testing progress:

### **Section Completion**

| **Section** | **Tested** | **Pass** | **Fail** | **Notes** |
|-------------|-----------|---------|---------|-----------|
| 1. Dashboard | [ ] | [ ] | [ ] | |
| 2. Chat Interface | [ ] | [ ] | [ ] | |
| 3. Day Book | [ ] | [ ] | [ ] | |
| 4. Receipt Voucher | [ ] | [ ] | [ ] | |
| 5. Payment Voucher | [ ] | [ ] | [ ] | |
| 6. Sales Invoice | [ ] | [ ] | [ ] | |
| 7. Contact View | [ ] | [ ] | [ ] | |
| 8. Outstanding Report | [ ] | [ ] | [ ] | |
| 9. Balance Sheet | [ ] | [ ] | [ ] | |
| 10. AI/NLP | [ ] | [ ] | [ ] | |
| 11. Autocomplete | [ ] | [ ] | [ ] | |
| 12. Tally Sync | [ ] | [ ] | [ ] | |
| 13. Database | [ ] | [ ] | [ ] | |
| 14. UI/UX | [ ] | [ ] | [ ] | |
| 15. Performance | [ ] | [ ] | [ ] | |
| 16. Error Recovery | [ ] | [ ] | [ ] | |
| 17. Security | [ ] | [ ] | [ ] | |
| 18. GSTIN/Tax | [ ] | [ ] | [ ] | |

**Overall Score**: ___/18 Sections Passed

---

## 🔧 TROUBLESHOOTING GUIDE

### **Common Issues**

**Issue 1: "Cannot connect to backend"**
```
Symptom: All API calls fail
Solution:
1. Check backend is running: http://localhost:8001/docs
2. Check terminal for backend errors
3. Restart backend: uvicorn backend.api:app --reload --port 8001
```

**Issue 2: "Tally connection failed"**
```
Symptom: Voucher creation fails, reports don't load
Solution:
1. Open Tally
2. Go to: Gateway → F12 (Configure)
3. Enable "HTTP Server" on port 9000
4. Restart Tally if needed
```

**Issue 3: "Autocomplete not working"**
```
Symptom: No suggestions when typing party name
Solution:
1. Check Tally is running
2. Check Tally company name matches .env: TALLY_COMPANY
3. Test endpoint manually: http://localhost:8001/ledgers/search?query=Cash
4. Check browser console for errors
```

**Issue 4: "AI responses are slow"**
```
Symptom: Takes > 10 seconds to respond
Solution:
1. Check GOOGLE_API_KEY is set in .env
2. Check internet connection (Gemini is cloud-based)
3. Check API quota (free tier has limits)
```

**Issue 5: "Voucher created in K24 but not in Tally"**
```
Symptom: Shows in /daybook but not in Tally
Solution:
1. Check database: sync_status column
2. If "ERROR", check backend logs for Tally error message
3. Common causes:
   - Wrong ledger name
   - Date format issue
   - Tally company locked
```

---

## 📝 TESTING LOG TEMPLATE

Use this format to document your testing sessions:

```
Date: _____________
Tester: _____________
Version: _____________

Test Session Log:
-----------------

Test 1: [Feature Name]
Time: [HH:MM]
Steps:
1. 
2. 
3. 

Expected: 
Actual: 
Status: [ ] Pass [ ] Fail

Issues Found:
-

Screenshots/Evidence:
-

---

[Repeat for each test]
```

---

## 🎯 PRE-LAUNCH CHECKLIST

Before going live with K24:

### **Functionality**
- [ ] All critical flows tested and passing
- [ ] No console errors in browser
- [ ] No Python errors in backend log
- [ ] Tally sync working bidirectionally
- [ ] AI chat responding correctly

### **Data Integrity**
- [ ] Test vouchers match Tally exactly
- [ ] Reports match Tally reports
- [ ] No duplicate vouchers
- [ ] Autocomplete shows all ledgers

### **Performance**
- [ ] Page loads < 2 seconds
- [ ] API responses < 1 second
- [ ] No lag with 1000+ vouchers

### **User Experience**
- [ ] Input clears after submission ✅
- [ ] Loading states visible
- [ ] Error messages clear
- [ ] Success feedback present

### **Security**
- [ ] API key required on all endpoints
- [ ] .env file not committed to git
- [ ] Sensitive data not exposed in logs

### **Documentation**
- [ ] This testing guide complete
- [ ] User manual created (if needed)
- [ ] Known issues documented

---

## 🚀 QUICK START: 5-MINUTE SMOKE TEST

If you're short on time, run this quick test to verify the system is working:

```
1. Start Tally (http://localhost:9000)
2. Start Backend (uvicorn backend.api:app --reload --port 8001)
3. Start Frontend (npm run dev in /frontend)
4. Open http://localhost:3000

5-Minute Test:
✓ See dashboard → Input field visible
✓ Type "Show daybook" → Daybook opens
✓ Click "New Receipt" → Form opens
✓ Type "Cash" in Party → Autocomplete works
✓ Fill amount 1000 → Click Create → Success

If all above pass: ✅ System is healthy!
If any fail: ⚠️ Review troubleshooting section
```

---

## 📚 ADDITIONAL RESOURCES

- **API Documentation**: `http://localhost:8001/docs` (Swagger UI)
- **Tally XML API**: Tally Solutions official docs
- **K24 Architecture**: See `COMPLETE_WALKTHROUGH.md`
- **UX Improvements**: See `UX_POLISH_MASTERPLAN.md`

---

**Happy Testing! 🎉**

**Remember**: Testing is not about finding what works, it's about finding what *doesn't* work so we can fix it before users encounter issues.

---

**Last Updated**: 2025-11-28  
**Document Version**: 1.0  
**Maintainer**: K24 Team
