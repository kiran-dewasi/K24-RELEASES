# K24.ai UX Copy Guidelines

## 1. Tone of Voice
Our voice is **Professional yet Approachable**. We are a helpful financial assistant, not a robotic system.

*   **Clarity First**: Financial data can be complex. Explain things simply.
*   **Concise**: Indian SMB owners are busy. Get to the point.
*   **Encouraging**: Use positive reinforcement ("Great job!", "All clear").
*   **No Jargon**: Avoid "Debit/Credit" where "Money In/Money Out" works better, unless dealing with specific accounting entry screens.

---

## 2. Copy Patterns

### A. Empty States
Never just say "No data found". Always explain **why** and **how to fix it**.

| Context | ❌ Bad | ✅ Good |
| :--- | :--- | :--- |
| **New Invoice List** | No invoices found. | **No invoices created yet.**<br>Create your first sale to start tracking revenue.<br>[+ Create Invoice] |
| **Search Results** | 0 results. | **We couldn't find "Acme Corp".**<br>Check the spelling or try searching by GST number. |
| **Pending Sync** | Data not available. | **Waiting for Tally Sync...**<br>Ensure Tally is open and Tally Connector is running. |

### B. Success Messages
Highlight the impact of the action, don't just state the technical result.

*   **Instead of:** "Invoice #001 saved."
*   **Say:** "Invoice #001 created and queued for Tally sync."
*   **Instead of:** "Settings updated."
*   **Say:** "Preferences saved. Your dashboard will now reflect these changes."

### C. Error Banners
Be transparent, reassuring, and actionable.

*   **Structure:** [What happened] + [Is data safe?] + [How to fix].
*   **Example:** "Connection lost. Your draft is safe locally. Please check your internet or retry."

---

## 3. Micro-Copy Examples

### Sync Status
*   **Syncing:** "Syncing with Tally... (24% complete)"
*   **Success:** "Synced just now. Data is up-to-date."
*   **Offline:** "Tally is offline. Last synced: 2 hours ago."
*   **Error:** "Sync failed. Tally might be closed. [Retry]"

### Dashboard Widgets (Zero State)
*   **Receivables:**
    *   *Headline:* **You're all caught up!**
    *   *Body:* "No outstanding payments from customers. Great work on collections."
*   **Payables:**
    *   *Headline:* **No bills due nearby.**
    *   *Body:* "You have cleared all immediate vendor payments."

### Invoice Table (No Data)
*   *Headline:* **Start your business day.**
*   *Body:* "Create invoices, record receipts, or sync existing data from Tally to see transactions here."
*   *CTA:* [Creates Sales Invoice] or [Sync Now]

### GST Alerts
*   **Due Soon (Amber):** "GSTR-1 is due in 3 days (Nov 11). avoiding late fees starts now."
*   **Overdue (Red):** "GSTR-3B was due yesterday. File immediately to minimize penalties."

### KITTU (AI Assistant)
*   **Welcome Message:**
    *   "Good morning, Kiran! Your cashflow looks healthy today. How can I help you?"
*   **Suggestion Chips:**
    *   "Show top debtors"
    *   "Create invoice for TATA"
    *   "What is my GST liability?"
*   **Follow-up Prompt (Ambiguous Request):**
    *   *User:* "Create invoice."
    *   *KITTU:* "Sure. Who is this invoice for? (e.g., 'ABC Corp')"
*   **Success Confirmation:**
    *   "Done! I've drafted a sales invoice for ABC Corp for ₹12,500. [View Draft]"

### Tooltips
*   **TDS:** "Tax Deducted at Source on payments made to contractors or professionals."
*   **Input Credit:** "GST paid on purchases that can be offset against your liability."
*   **Ledger Scrutiny:** "AI check for unusual entries or classification errors."
