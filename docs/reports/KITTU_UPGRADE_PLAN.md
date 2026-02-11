# KITTU Agent Orchestration: The "Executive Brief" Upgrade

## 1. The Core Philosophy: "Executive Briefing"
You are right. A business owner doesn't want a wall of text. They want:
1.  **The Answer** (Immediate, concise).
2.  **The Action** (One-click execution).
3.  **The Context** (Visuals/Cards, not text).

If you ask about the Balance Sheet, KITTU shouldn't *describe* it. It should **take you there** or **show it** instantly.

---

## 2. The "Antigravity-Style" Interface
We will mirror the experience you have here with me (Antigravity).
*   **Streaming Responses**: Text appears as it's thought, not in one big dump.
*   **Rich UI Widgets**: Instead of text tables, we render **Interactive Cards** (React Components) right in the chat.
*   **Navigation Actions**: The agent can control the app. If it says "Here is the Balance Sheet", the app *automatically navigates* to `/reports/balance-sheet`.

---

## 3. Revised Architecture: The "Director" Pattern

The Orchestrator will now act as a **Director**, not just a writer. It controls the *entire screen*, not just the chat bubble.

### A. The Response Protocol
We will enforce a strict "No Wall of Text" policy. The LLM will be instructed to output a JSON structure that separates **Speech** from **Action**.

**Example User Query:** "How is my cash flow?"

**Old Response (Bad):**
> "Your cash flow is looking okay. You have 50,000 in hand and 20,000 in the bank. Last month it was lower. You should check your receivables..." (Boring, long).

**New Response (Executive):**
```json
{
  "speech": "Your cash position is healthy at ₹70k total.",
  "widget": {
    "type": "KPI_CARD",
    "data": { "cash_in_hand": 50000, "bank": 20000, "trend": "+12%" }
  },
  "action": {
    "type": "NAVIGATE",
    "path": "/reports/cash-book"
  }
}
```
**User Experience:**
1.  KITTU says: *"Your cash position is healthy at ₹70k total."*
2.  A beautiful **Green KPI Card** pops up showing the numbers.
3.  A button appears: **"Open Cash Book"** (or it auto-navigates).

### B. The "Antigravity" Chat Experience
To achieve the "Antigravity" feel (where I am an agent working *with* you), we need:
1.  **Thinking State**: Show "KITTU is analyzing ledgers..." (transparency).
2.  **Tool Usage**: Show "Checking Tally..." -> "Found 3 discrepancies."
3.  **Sidebar/Overlay**: The chat shouldn't be a tiny box. It should be a **Command Center** that can expand or overlay the screen.

---

## 4. Refined Implementation Plan

### Phase 1: The "Director" Orchestrator (Backend)
*   **Task**: Rewrite `orchestrator.py` to output **Structured Actions** instead of just text strings.
*   **Logic**:
    *   If intent is `QUERY_DATA` -> Return `Widget` + `Short Summary`.
    *   If intent is `NAVIGATION` -> Return `Navigate Action`.
    *   If intent is `TRANSACTION` -> Return `Draft Card` (Approve/Reject).

### Phase 2: The "Rich Chat" UI (Frontend)
*   **Task**: Upgrade `MagicInput.tsx` and `ChatPage` to render these new widgets.
*   **Features**:
    *   Support for `KPI_CARD`, `CHART_CARD`, `NAVIGATION_EVENT`.
    *   "Streaming" text effect.
    *   Auto-scroll to relevant data.

### Phase 3: Context Awareness
*   **Task**: Feed the *current page* to the AI.
*   **Scenario**: You are on the "Sales Register" page. You ask "Filter for last week".
*   **Result**: The AI knows you are on Sales Register and applies the filter *to that view* instead of giving a generic answer.

## 5. Next Steps
I will update the `KITTU_UPGRADE_PLAN.md` to reflect this "Executive Brief" approach. Then, I will start by modifying the **Backend Orchestrator** to support this "Action-First" response format.
