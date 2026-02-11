# KITTU Upgrade: Phase 2 - Context Awareness

## Goal
Make KITTU "see" what you see. If you are on the **Sales Register** page and say "Filter for last week", KITTU should know you mean *Sales*, not Purchases.

## Implementation Plan

### 1. Frontend: Pass Context to Backend
*   **Action**: Update `MagicInput.tsx` to accept a `context` prop (e.g., `{ page: 'sales-register', filters: {...} }`).
*   **Action**: In `handleMagic`, send this `context` object to the `/chat` endpoint.

### 2. Backend: Use Context in Reasoning
*   **Action**: Update `ChatRequest` model in `api.py` to accept `client_context`.
*   **Action**: Update `IntentRecognizer` to use this context for disambiguation.
    *   *User*: "Filter for last week"
    *   *Without Context*: "Filter what?"
    *   *With Context (Sales Page)*: `Intent: FILTER_DATA`, `Entity: Sales`, `Params: { timeframe: 'last_week' }`

### 3. Backend: "Action-at-a-Distance"
*   **Action**: If the intent is to *change the view* (e.g., filter), return a `UI_ACTION` response.
*   **Frontend**: `MagicInput` receives `UI_ACTION` and triggers a callback to update the parent page's state.

---

## Execution Steps
1.  **Modify `api.py`**: Add `client_context` to `ChatRequest`.
2.  **Modify `MagicInput.tsx`**: Add `pageContext` prop and send it.
3.  **Modify `IntentRecognizer`**: Inject page context into the LLM prompt.
