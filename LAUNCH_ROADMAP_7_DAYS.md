# 🚀 K24 Desktop Launch Roadmap (7 Days to Beta)
**Goal**: Functional desktop app with core WhatsApp + Tally automation working

---

## 📅 Day 1 (Today - Jan 27): Foundation Fixes
**Morning (2-3 hours): Critical Blockers**
- **Priority 1: Fix Auth (BLOCKER)**
  - [ ] Local SQLite auth without Supabase dependency
  - [ ] Default user login working (`kittu@krishasales.com`)
  - [ ] JWT token generation/validation
  - [ ] Test: Can login → reach dashboard

- **Priority 2: Hide Compliance Tab (Quick Win)**
  - [ ] Comment out compliance routes in sidebar
  - [ ] Add "Coming Soon" placeholder page
  - [ ] Test: Sidebar clean, no compliance visible

**Afternoon (2-3 hours): Core Data Flow**
- **Priority 3: Verify Tally Connection**
  - [ ] Test Tally agent on port 9000
  - [ ] Fetch sample ledgers (basic pull test)
  - [ ] Push 1 simple voucher to Tally (basic push test)
  - [ ] Test: Desktop ↔ Tally bidirectional works

**Evening: Smoke Test**
- [ ] Login works
- [ ] Dashboard loads with sample data
- [ ] Tally agent responds to ping

---

## 📅 Day 2 (Jan 28): AI Agent Upgrade
**Morning: Multi-Item Bill Processing**
- **Priority 4: Rewrite AI Prompt (CRITICAL)**
  - [ ] Modify `agent_gemini.py` to extract line items:
    ```python
    # Current (single amount)
    {total: 5000}

    # Target (multi-item)
    {
      items: [
        {name: "Product A", qty: 10, rate: 500, unit: "Nos"},
        {name: "Product B", qty: 5, rate: 200, unit: "Kgs"}
      ]
    }
    ```
  - [ ] Update Tally XML generator for multi-item vouchers
  - [ ] Test: Send bill with 3 items → all 3 appear in Tally

**Afternoon: Zero-Question Logic**
- **Priority 5: Confidence-Based Auto-Execution**
  - [ ] Implement confidence scoring in `agent_orchestrator_v2.py`
  - [ ] Logic: If confidence > 95% → auto-post, else → ask
  - [ ] Add fallback: Default unit = "Kgs" if not detected
  - [ ] Test:
    - Clear bill → auto-posts without asking
    - Unclear bill → asks ONE question only

**Evening: Unit Detection**
- [ ] Train/fine-tune prompt to detect units (Nos, Kgs, Ltr, Box)
- [ ] Default to "Kgs" if unit missing
- [ ] Test: Bill without units → defaults to Kgs correctly

---

## 📅 Day 3 (Jan 29): Real-Time Sync + Parallel Processing
**Morning: Background Sync Loop**
- **Priority 6: Activate Real-Time Pull**
  - [ ] Create `scripts/sync_loop.py`:
    ```python
    while True:
      fetch_ledgers_from_tally()
      fetch_vouchers_from_tally()
      update_local_sqlite()
      sleep(5)  # Every 5 seconds
    ```
  - [ ] Run as background service (systemd/Task Scheduler)
  - [ ] Test: Create voucher in Tally → appears in desktop within 5 sec

**Afternoon: Parallel Bill Processing**
- **Priority 7: Message Queue (Celery/BullMQ)**
  - [ ] Setup Redis queue
  - [ ] Modify Baileys listener to queue messages
  - [ ] Process 10 bills in parallel (not sequential)
  - [ ] Test: Send 10 bills at once → all process in ~10 sec total

**Evening: Performance Testing**
- [ ] Stress test: 50 bills uploaded
- [ ] Check SQLite performance
- [ ] Optimize slow queries

---

## 📅 Day 4 (Jan 30): WhatsApp Phone Mapping
**Morning: Supabase Schema Setup**
- [ ] Create `whatsapp_customer_mappings` table
- [ ] Create `whatsapp_routing_cache` table
- [ ] Setup row-level security policies
- [ ] Test: Can insert/query mappings

**Afternoon: Routing Logic**
- [ ] Implement phone → user_id lookup in Baileys
- [ ] Conflict resolution (ask for code if multiple matches)
- [ ] Cache mechanism (24-hour sessions)
- [ ] Test:
  - 1 customer → auto-routes
  - 2 users have same customer → asks for code

**Evening: Frontend for Adding Customers**
- [ ] Settings page: "WhatsApp Customers"
- [ ] Form: Add customer (name, phone, optional code)
- [ ] List view with edit/delete
- [ ] Test: User can register 5 customers

---

## 📅 Day 5 (Jan 31): Data Export (PDF/Excel)
**Morning: PDF Generation**
- [ ] Install ReportLab/WeasyPrint
- [ ] Create Tally-style invoice template
- [ ] Endpoint: `/api/reports/invoice/{voucher_id}/pdf`
- [ ] Test: Generate PDF from sample voucher

**Afternoon: Excel Export**
- [ ] Install openpyxl
- [ ] Export vouchers/ledgers to .xlsx
- [ ] Endpoint: `/api/reports/export?format=excel&type=sales`
- [ ] Test: Export last month's data to Excel

**Evening: WhatsApp Integration**
- [ ] Modify agent to detect format request:
  - "Send as PDF" → generate PDF
  - "Export to Excel" → generate Excel
  - Default → text summary
- [ ] Test:
  - "Show invoice 101 as PDF" → sends PDF
  - "Export January sales" → sends Excel

---

## 📅 Day 6 (Feb 1): 360° Views (MVP)
**Morning: Customer 360 Backend**
- [ ] Aggregation query: All transactions for customer
- [ ] Calculate: Outstanding, payment history, aging
- [ ] Endpoint: `/api/customers/{customer_id}/360`
- [ ] Test: Returns complete customer data

**Afternoon: Customer 360 Frontend**
- [ ] New page: `/customers/{id}`
- [ ] Sections:
  - Summary (total sales, outstanding)
  - Transaction history (table)
  - Payment timeline (chart)
  - Quick actions (send reminder, add payment)
- [ ] Test: Click customer → see full 360° view

**Evening: Item 360 (Simplified)**
- [ ] Backend: `/api/items/{item_id}/360`
- [ ] Frontend: `/items/{id}`
- [ ] Show: Stock, purchase/sale history, profit margin
- [ ] Test: Works for top 10 items

---

## 📅 Day 7 (Feb 2): Polish + Desktop Packaging
**Morning: UX Polish**
- [ ] Loading states (skeletons, spinners)
- [ ] Error handling (user-friendly messages)
- [ ] Success toasts/confirmations
- [ ] Responsive design fixes
- [ ] Test: No janky UI, smooth experience

**Afternoon: Desktop Packaging Prep**
- [ ] Tauri configuration (`tauri.conf.json`)
- [ ] Backend as sidecar (bundle FastAPI exe)
- [ ] Implement Deep Link Handler (`k24://auth`)
- [ ] Update Onboarding: Remove local questions, add "Connect with K24.ai Web" button
- [ ] Test build: `npm run tauri build`
- [ ] Test: .exe installs on clean Windows VM

**Evening: End-to-End Testing**
- **Full workflow test**:
  1. Install app on fresh machine
  2. Login with default credentials
  3. Connect to Tally (port 9000)
  4. Send bill via WhatsApp
  5. Bill auto-processes → posts to Tally
  6. Pull data from Tally → shows in dashboard
  7. Generate PDF report
  8. View customer 360° profile

---

## 🎯 Success Criteria (Launch-Ready Checklist)
**Must-Have (Blocking Launch)**
- ✅ Auth works without Supabase
- ✅ Multi-item bill processing (3+ items per invoice)
- ✅ Tally push & pull working
- ✅ Zero-question agent (95%+ confidence auto-post)
- ✅ WhatsApp phone mapping functional
- ✅ Parallel processing (10 bills at once)
- ✅ Desktop .exe builds successfully

**Should-Have (Launch with Limited Features)**
- ✅ PDF/Excel export working
- ✅ Real-time sync (5-second interval)
- ✅ Customer 360° view (simplified)
- ✅ Basic error handling

**Nice-to-Have (Post-Launch)**
- 🔄 Item 360° view (full version)
- 🔄 Advanced reporting dashboards
- 🔄 Multi-device sync
- 🔄 Cloud backups

---

## ⚡ Daily Stand-Up Format (Track Progress)
**Every Evening (6 PM):**
```text
✅ Completed Today:
- Task 1
- Task 2

🚧 In Progress:
- Task 3 (50% done)

🔴 Blockers:
- Issue X (needs resolution)

📋 Tomorrow's Plan:
- Task 4
- Task 5
```
