# K24.ai Interaction & API Specification

This document defines the standard for UI/UX interactions and their backend connectivity. **No visible UI element should exist without a defined backend path or a clear "Coming Soon" state.**

## Core Principles

1.  **No Dead Clicks**: Every interactive element must trigger a feedback loop (loading state -> success/error).
2.  **Explicit States**:
    *   **Idle**: Default state.
    *   **Loading**: Spinner on button, progress bar, or skeleton loader.
    *   **Success**: Toast notification, ephemeral checkmark, or data update.
    *   **Error**:
        *   *Recoverable*: "Sync failed. Retry?" (Inline action).
        *   *Unrecoverable*: "System error. View logs." (Link to support/logs).
3.  **Visual Continuity**:
    *   Avoid nested cards (box-in-box).
    *   Use whitespace for separation, not borders.
    *   Align content to a single vertical grid.

---

## Engineer's Checklist (Pre-Ship)

Before merging any new screen or feature:

- [ ] **Endpoint Verification**: Does the button mapped to a real API URL? (No `console.log` stubs).
- [ ] **Loading State**: Is the button disabled and showing a spinner `isSubmitting`?
- [ ] **Error Handling**: logic implements `try/catch` and displays a user-friendly error message (not `[bject Object]`).
- [ ] **Success Feedback**: Does the UI update immediately (optimistic) or show a success toast?
- [ ] **Empty State**: Is there a clear design for 0 items?
- [ ] **Responsiveness**: Does it break on mobile/tablet?

---

## Feature Specifications

### 1. Dashboard (`/`)
*   **Goal**: High-level overview.
*   **Data Source**: `GET /api/dashboard/activities`, `GET /compliance/dashboard-stats`.
*   **Interactions**:
    *   *Refresh Stats*:
        *   Trigger: Auto-poll every 5m or Pull-to-refresh.
        *   Loading: Skeleton loaders on stat cards.
        *   Error: "Could not load latest stats." (Toast).
    *   *Quick Actions (e.g., New Invoice)*:
        *   Trigger: Navigation button.
        *   Feedback: Immediate route change.

### 2. Invoices (`/invoices`)
*   **Goal**: Manage sales and purchases.
*   **Data Source**: `GET /api/vouchers?type=Sales`.
*   **Interactions**:
    *   *Create Invoice*:
        *   Endpoint: `POST /api/vouchers/sales`.
        *   Loading: "Creating..." on submit button.
        *   Success: Redirect to detail view + "Invoice #123 created" toast.
        *   Error 400: Highlight invalid fields.
        *   Error 500: "Server error. Try again later."
    *   *Sync to Tally*:
        *   Endpoint: `POST /api/vouchers/{id}/sync` (Proposed).
        *   State: `status: 'syncing'` -> `status: 'synced'` | `status: 'failed'`.

### 3. Daybook (`/daybook`)
*   **Goal**: Audit trail.
*   **Data Source**: `GET /api/vouchers`.
*   **Interactions**:
    *   *Filter*:
        *   Local state change triggers new fetch.
        *   Loading: Table opacity 50% or progress bar.
    *   *Export*:
        *   Endpoint: `GET /reports/sales-register` (closest match).
        *   Loading: "Generating..." button state.

### 4. Settings (`/settings`)
*   **WhatsApp Integration**:
    *   *Generate QR*: `GET /api/whatsapp/qr`.
    *   *Status*: `GET /api/baileys/status`.
    *   **States**:
        *   `CONNECTED`: Green badge.
        *   `DISCONNECTED`: Red badge + "Reconnect" button.
        *   `QR_READY`: Show QR Canvas.
*   **Tally Connector**:
    *   *Status*: `GET /api/health/tally`.
    *   *Resync*: `POST /api/tally/full-sync`.

### 5. AI Assistant (KITTU)
*   **Goal**: Chat-based operations.
*   **Data Source**: `POST /api/chat`.
*   **Interactions**:
    *   *Send Message*:
        *   Optimistic: Append user message immediately.
        *   Loading: "Kittu is typing..." animation.
        *   Success: Stream response or append final markdown.
        *   Error: Red retry icon next to message.

---

## Visual Guidelines (The "De-Box" Initiative)

To achieve a premium, fluid feel:

1.  **Main Canvas**: Use `#FBFBFB` or White as the main background.
2.  **No Double Borders**: Do not place a Card with a border inside a Container with a border.
3.  **Headings**: Page titles should be outside the content cards, directly on the canvas, aligned with the left edge of the content.
4.  **Shadows**: Use `shadow-sm` for interactive elements (cards, buttons), `shadow-none` for static groupings.
5.  **Dividers**: Prefer `border-b` on headers over boxing the whole section.
