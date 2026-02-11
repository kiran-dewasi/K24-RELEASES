# 🧪 K24 - Non-Technical User Testing Guide

## Pre-Test Checklist

### Your Setup (Before Users Arrive)
- [ ] Backend running: `uvicorn backend.api:app --reload --port 8001`
- [ ] Frontend running: `npm run dev` (in frontend folder)
- [ ] Tally is open with a test company loaded
- [ ] Tally HTTP server enabled (Port 9000)
- [ ] Test the onboarding yourself once
- [ ] Clear browser cache/localStorage
- [ ] Have a notepad ready for feedback

### Test Environment
- [ ] Good internet connection (for AI features)
- [ ] Tally Educational or Premium version
- [ ] Chrome/Edge browser (recommended)
- [ ] Screen recording software (optional but helpful)

---

## 5-Minute Demo Script

### **Opening** (30 seconds)
> "Hi! Thanks for testing K24. This is an accounting software that makes Tally easier to use. 
> Instead of clicking through menus, you can just type what you want. 
> Let me show you how to set it up - it takes about 2 minutes."

### **Step 1: Account Creation** (1 minute)
1. Open browser: `http://localhost:3000/onboarding`
2. Say: "First, let's create your account. Use any email - it doesn't need to be real for testing."
3. Help them fill:
   - Full Name: Their actual name
   - Email: `test@example.com` (or their choice)
   - Username: `testuser` (or their choice)
   - Password: `Test1234` (simple for testing)
4. Click "Continue"

**Watch for**: Confusion about password requirements, email format

### **Step 2: Company Details** (1 minute)
1. Say: "Now enter your company details. This is what will appear on invoices."
2. Help them fill:
   - Company Name: Their company or "Test Company"
   - GSTIN: `07AABCS1234Q1Z5` (sample)
   - PAN: `AABCS1234Q` (sample)
   - Rest is optional
3. Click "Continue"

**Watch for**: Confusion about GSTIN format, what fields are required

### **Step 3: Tally Setup** (1.5 minutes)
1. Say: "This is the important part - connecting to Tally."
2. **First, show them Tally**:
   - Open Tally
   - Show the company name at the top
   - Say: "See this company name? We need to type it EXACTLY as shown."
3. Help them:
   - Tally Company Name: Copy exact name from Tally
   - Tally URL: Leave as `http://localhost:9000`
   - Educational Mode: Check if using Tally Educational
4. Click "Continue"

**Watch for**: Typos in company name, confusion about EDU mode

### **Step 4: AI Features** (30 seconds)
1. Say: "This enables AI features - you can skip it for now."
2. Click "Complete Setup"

**Watch for**: Questions about what AI does, whether it's required

### **First Transaction** (1 minute)
1. Say: "Great! Now let's create your first receipt."
2. Navigate to Daybook (should auto-redirect)
3. Click "New Receipt"
4. Help them create a simple receipt:
   - Party: "ABC Corp"
   - Amount: 10000
   - Narration: "Test payment"
5. Click "Create"
6. **Show them Tally**: Open Tally Daybook, show the entry appeared!

**Watch for**: Excitement when they see it in Tally, confusion about fields

---

## User Testing Scenarios

### Scenario 1: Complete Beginner (Never used Tally)
**Goal**: Can they complete onboarding without help?

**Test**:
1. Give them the URL: `http://localhost:3000/onboarding`
2. Say: "Try to set up an account. I'm here if you get stuck."
3. **Don't help unless they ask**
4. Note where they get confused

**Success Criteria**:
- [ ] Completes all 4 steps
- [ ] Understands what each field means
- [ ] Doesn't get frustrated

### Scenario 2: Tally User (Knows Tally basics)
**Goal**: Do they see the value over Tally?

**Test**:
1. Complete onboarding together
2. Ask them to create 3 receipts:
   - One in K24
   - One in Tally (traditional way)
   - One in K24 again
3. Ask: "Which was faster?"

**Success Criteria**:
- [ ] Prefers K24 after trying both
- [ ] Understands time-saving benefit
- [ ] Asks about other features

### Scenario 3: Accountant (Professional user)
**Goal**: Would they use this for clients?

**Test**:
1. Show them the Audit Dashboard
2. Show them PDF export
3. Ask: "Would this help with your CA practice?"

**Success Criteria**:
- [ ] Sees professional value
- [ ] Asks about pricing
- [ ] Wants to try with real data

---

## Questions to Ask (After Testing)

### Onboarding Experience
1. "On a scale of 1-10, how easy was the setup?"
2. "Which step was most confusing?"
3. "Did you understand what each field was for?"
4. "Would you do this without my help?"

### Feature Understanding
1. "What do you think K24 does?"
2. "How is it different from Tally?"
3. "What would you use it for?"

### Value Perception
1. "Would you pay for this? How much?"
2. "What features are missing?"
3. "Would you recommend it to others?"

### UI/Design
1. "Does it look professional?"
2. "Is anything confusing or unclear?"
3. "Is the text easy to read?"

---

## Common Issues & Quick Fixes

### Issue 1: "Cannot connect to Tally"
**Likely Cause**: Tally HTTP server not enabled

**Fix**:
1. Open Tally
2. Press `F1` (Help)
3. Type "Configuration"
4. Go to: Connectivity → Client/Server
5. Set "Enable Server" = Yes
6. Port = 9000
7. Restart Tally

**Show User**: Take them through this once, they'll remember

---

### Issue 2: "Company name doesn't match"
**Likely Cause**: Typo or extra spaces

**Fix**:
1. Open Tally
2. Look at company name at top of screen
3. Copy it EXACTLY (including spaces, capitals)
4. Paste in K24

**Show User**: Use copy-paste, don't type manually

---

### Issue 3: "Transaction not showing in Tally"
**Likely Cause**: Wrong company loaded in Tally

**Fix**:
1. Check Tally company name matches K24 setup
2. Refresh Tally Daybook (Ctrl+R)
3. Check if company is in EDU mode

**Show User**: Always keep Tally open while using K24

---

### Issue 4: "Password too weak"
**Likely Cause**: Less than 8 characters

**Fix**:
1. Use at least 8 characters
2. Mix letters and numbers
3. Example: `MyPass123`

**Show User**: Password strength indicator (if we add it)

---

### Issue 5: "Page not loading"
**Likely Cause**: Backend/Frontend not running

**Fix**:
1. Check terminal - is backend running?
2. Check frontend terminal - any errors?
3. Try: `http://127.0.0.1:3000` instead of `localhost`

**Show User**: "Sometimes you need to refresh the page"

---

## Feedback Collection

### During Test (Observe & Note)
- Where do they pause/hesitate?
- What do they click first?
- Do they read instructions?
- What questions do they ask?
- What makes them smile/frustrated?

### After Test (Ask & Record)
Create a simple Google Form with:

**Section 1: About You**
- Name (optional)
- Profession (CA/Accountant/Business Owner/Other)
- Tally experience (Beginner/Intermediate/Expert)

**Section 2: Onboarding (1-5 stars)**
- How easy was account creation?
- How clear were the instructions?
- Did you understand the Tally setup?
- Overall onboarding experience?

**Section 3: Features (Yes/No)**
- Did the transaction sync to Tally?
- Did you try the PDF export?
- Did you explore the Daybook?
- Would you use the AI chat?

**Section 4: Value (Open-ended)**
- What did you like most?
- What was confusing?
- What features are missing?
- Would you pay for this? How much?
- Any other feedback?

---

## Success Metrics

### Quantitative
- **Completion Rate**: % who finish onboarding
- **Time to First Transaction**: How long from signup to first voucher
- **Error Rate**: How many get stuck/need help
- **Tally Sync Success**: % of transactions that sync correctly

### Qualitative
- **Excitement Level**: Do they say "wow" or "cool"?
- **Understanding**: Do they get what K24 does?
- **Willingness to Pay**: Would they actually buy it?
- **Referral Intent**: Would they tell others?

---

## Red Flags to Watch For

### Critical Issues (Fix Immediately)
- [ ] User can't complete onboarding
- [ ] Transactions don't sync to Tally
- [ ] Page crashes or freezes
- [ ] Data gets lost
- [ ] Security concerns raised

### Important Issues (Fix Soon)
- [ ] Confusing instructions
- [ ] Unclear error messages
- [ ] Slow performance
- [ ] Missing obvious features
- [ ] Unprofessional appearance

### Nice-to-Fix Issues (Future)
- [ ] Minor UI tweaks
- [ ] Additional features requested
- [ ] Preference differences
- [ ] Edge case bugs

---

## Post-Test Actions

### Immediate (Same Day)
1. Thank the tester
2. Note down all feedback
3. Fix any critical bugs
4. Update documentation if needed

### Short-term (Within Week)
1. Compile all feedback
2. Prioritize issues
3. Fix important bugs
4. Improve confusing parts

### Long-term (Before Launch)
1. Test with 10+ users
2. Achieve 80%+ completion rate
3. Get 4+ star average rating
4. Collect testimonials

---

## Sample Test Schedule

### Day 1: Friends & Family (3 people)
- **Goal**: Find obvious bugs
- **Profile**: Mix of tech-savvy and non-tech
- **Duration**: 30 mins each
- **Focus**: Can they complete onboarding?

### Day 2: Accountants (3 people)
- **Goal**: Professional validation
- **Profile**: CAs or bookkeepers
- **Duration**: 45 mins each
- **Focus**: Would they use it professionally?

### Day 3: Business Owners (3 people)
- **Goal**: End-user perspective
- **Profile**: Small business owners
- **Duration**: 30 mins each
- **Focus**: Does it solve their problems?

### Day 4: Tally Experts (2 people)
- **Goal**: Technical validation
- **Profile**: Tally power users
- **Duration**: 60 mins each
- **Focus**: Feature completeness, edge cases

### Day 5: Review & Refine
- **Goal**: Consolidate feedback
- **Action**: Fix critical issues
- **Prepare**: For beta launch

---

## Tester Incentives

### What to Offer
- **Free lifetime Pro account** (worth ₹9,999)
- **Early access** to new features
- **Name in credits** (if they want)
- **Referral bonus** (₹500 per referral)

### How to Position It
> "You're helping build something that will save accountants 10+ hours every week. 
> In return, you'll get lifetime free access (worth ₹9,999) and your name in the credits. 
> Plus, if you refer other testers, you get ₹500 per person!"

---

## Emergency Contact Card

Give this to testers:

```
┌─────────────────────────────────────┐
│         K24 TESTING SUPPORT         │
├─────────────────────────────────────┤
│ If something breaks:                │
│                                     │
│ 📱 WhatsApp: +91-XXXXXXXXXX        │
│ 📧 Email: support@k24.app          │
│ 💬 Say: "K24 test issue"           │
│                                     │
│ I'll respond within 5 minutes!     │
└─────────────────────────────────────┘
```

---

## Final Checklist Before Each Test

**5 Minutes Before User Arrives**:
- [ ] Backend running (check `http://localhost:8001/docs`)
- [ ] Frontend running (check `http://localhost:3000`)
- [ ] Tally open with test company
- [ ] Tally HTTP enabled
- [ ] Browser cache cleared
- [ ] Notepad ready for notes
- [ ] Water/coffee for tester
- [ ] Smile and be welcoming! 😊

---

**Good luck with testing! Remember: Every confused user is a learning opportunity. 🚀**

**Pro Tip**: Record their screen (with permission) - you'll catch things you miss while watching!
