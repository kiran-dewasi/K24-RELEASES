# 🚀 Onboarding, Authentication, and Tenant Parsing Flow

This document details the complete flow of how a user enters the K24 system, how their account is created, how they are matched to a specific Tally instance (Tenant), and how the WhatsApp binding ties it all together.

## 1. High-Level Architecture

The system operates on a **Hybrid Architecture**:
1.  **Cloud Master (Supabase)**: Handles Authentication, User Profiles, and unique `TenantID` assignment.
2.  **Local Replica (Desktop/SQLite)**: The K24 Desktop App maintains a local copy of User/Tenant data to support **Offline-First** capability.

### The "Golden ID": `TenantID`
Every transaction, query, and configuration is scoped by a `TenantID` (e.g., `TENANT-12345678`). This ID links:
*   A User (Web/Desktop)
*   A Tally Instance (Local Port)
*   A WhatsApp Phone Number

---

## 2. Step-by-Step Flow

### Phase A: Registration (Sign Up)

1.  **User Action**: User fills Registration Form (Name, Email, Mobile, Company, Password).
2.  **API Call**: `POST /api/auth/register`
3.  **Backend Process**:
    *   **Step 1: Cloud Registration**: Calls Supabase `signUp`. Creation of Auth User.
    *   **Step 2: Tenant Assignment**:
        *   Checks if Supabase profile already has a `tenant_id`.
        *   If not, generates a unique ID: `TENANT-{UserID_First8Chars}`.
        *   Syncs this `tenant_id` back to Supabase metadata.
    *   **Step 3: Local Replication**:
        *   Creates a `User` record in local `k24.db`.
        *   Creates a `Tenant` record with the `tenant_id`.
        *   Creates a `Company` record linked to that `tenant_id`.
    *   **Step 4: Token Generation**: Issues a JWT Access Token containing `{"sub": "username", "tenant_id": "TENANT-XXX"}`.

**Result**: User is logged in, and their session is strictly bound to their unique Tenant ID.

### Phase B: Login (Checking Existing User)

1.  **User Action**: Enters Email/Password.
2.  **API Call**: `POST /api/auth/login`
3.  **Backend Process**:
    *   **Step 1: Cloud Auth**: Tries to authenticate with Supabase.
    *   **Step 2: Sync Check**:
        *   If Cloud Login succeeds but user *doesn't exist locally* (First time on this PC), the system **Auto-Pulls** user profile and `tenant_id` from cloud and creates local records.
        *   If Cloud is offline, it falls back to checking the password against the local database hash.
4.  **Token**: Returns JWT with the authoritative `tenant_id`.

---

## 3. Tenant-to-Tally Matching (The Bridge)

Once logged in, the system needs to know: *"Which Tally company belongs to this Tenant?"*

1.  **Setup Page**: User goes to Settings > Tally Setup.
2.  **Scan**: System scans ports 9000-9005.
3.  **Binding**: User selects their Tally Company (e.g., "Shree Ganesh Traders").
4.  **Storage**: Backend saves this mapping:
    *   `Tenant: TENANT-ABC` -> `TallyCompany: Shree Ganesh Traders` -> `TallyURL: http://localhost:9000`

**Validation**: When a user performs an action (e.g., "Create Invoice"), the backend:
1.  Reads `tenant_id` from JWT.
2.  Looks up the bound Tally Company for that tenant.
3.  Sends XML request to the specific Tally URL.

---

## 4. WhatsApp Binding logic

How does an incoming WhatsApp message find the right Tally?

1.  **Message Arrives**: From `+91 98765 43210`.
2.  **Lookup**: `baileys-listener` calls `/api/whatsapp/identify-user?phone=...`
3.  **Backend Logic**:
    *   Queries `Users` table for `whatsapp_number == +91 98765 43210`.
    *   **Found?** Returns `tenant_id` (e.g., `TENANT-ABC`).
    *   **Not Found?** Returns `Unknown`.
4.  **Context**: The listener now attaches `tenant_id` to all subsequent requests.
5.  **Execution**: The Query Orchestrator receives the query + tenant_id, connects to the correct Tally, and answers contextually.

---

## 5. Testing Guide: "How to break it"

Use this checklist to verify the flow handles reality.

### Scenario 1: Fresh Onboarding (The Happy Path)
- [ ] Go to `/signup`.
- [ ] Register with new email.
- [ ] Verify you are redirected to Dashboard.
- [ ] Check DB (`select * from users`): Ensure `tenant_id` starts with `TENANT-`.

### Scenario 2: Double Registration
- [ ] Try to Register *again* with the same email.
- [ ] Expected: Error "Email already registered".

### Scenario 3: First Login on New Device (Sync)
- [ ] (Simulated) Delete local User record from SQLite but keep Supabase account.
- [ ] Log in via UI.
- [ ] Expected: Login succeeds, and User record "Reappears" in SQLite (Synced from cloud).

### Scenario 4: Offline Login
- [ ] Disconnect Internet.
- [ ] Log in.
- [ ] Expected: Login succeeds (using local hash verification).

### Scenario 5: WhatsApp Unknown User
- [ ] Send message from a number NOT in the DB.
- [ ] Expected: Bot replies "Contact Admin to register".

### Scenario 6: WhatsApp Known User
- [ ] Update `users` table: set `whatsapp_number` = YOUR_NUMBER for your user.
- [ ] Send "Hi".
- [ ] Expected: Bot replies personally and can answer queries about YOUR tenant's data.
