# 🧪 K24 COMPLETE SYSTEM TEST - Nov 28, 2025 5:26 PM

**Environment**: Tally EDU Mode (TALLY_EDU_MODE=true in .env)

---

## TEST 1: Receipt Creation (Full Flow)

### Steps:
1. Navigate to http://localhost:3000/operations/receipt
2. Fill form:
   - Party: "TestCustomer2025"
   - Amount: 5000
   - Deposit To: Cash
   - Narration: "System test receipt"
3. Click "Save Receipt"

### Expected Results:
- ✅ Auto-create ledger "TestCustomer2025" under "Sundry Debtors" in Tally
- ✅ Create Receipt voucher with date = 20251101 (Nov 1, 2025 for EDU mode)
- ✅ Show success alert
- ✅ Redirect to /daybook
- ✅ Voucher visible in Tally Daybook

---

## TEST 2: Payment Creation

### Steps:
1. Navigate to http://localhost:3000/operations/payment
2. Fill form:
   - Party: "TestVendor2025"
   - Amount: 3000
   - Paid From: Cash
   - Narration: "System test payment"
3. Click "Create Payment"

### Expected Results:
- ✅ Auto-create ledger "TestVendor2025" under "Sundry Creditors" in Tally
- ✅ Create Payment voucher with date = 20251101
- ✅ Show success message
- ✅ Redirect to /daybook

---

## TEST 3: Navigation & Redirects

### Steps:
1. Navigate to http://localhost:3000
2. Check if redirected to /onboarding (if not configured) or Dashboard
3. Click "Operations" tab
4. Click "Create Receipt"
5. Click back button
6. Click "Reports" tab

### Expected Results:
- ✅ All navigation works smoothly
- ✅ No 404 errors
- ✅ Tabs switch properly

---

## TEST 4: Error Handling

### Steps:
1. Try to create Receipt with empty party name
2. Try to create Receipt with invalid amount (text)

### Expected Results:
- ✅ Clear error messages displayed
- ✅ Form validation prevents submission
- ✅ User-friendly error display

---

## TEST 5: Tally Data Pull (Sync)

### Steps:
1. Manually create a voucher in Tally
2. Navigate to http://localhost:3000/daybook
3. Check if voucher appears

### Expected Results:
- ✅ Sync pulls latest Tally data
- ✅ Daybook displays Tally vouchers

---

## AUTOMATED TEST EXECUTION

Running automated browser tests now...
