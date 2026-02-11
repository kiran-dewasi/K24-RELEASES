# K24 Desktop Device Authentication Flow

## Overview
This document outlines the authentication flow between the K24 Desktop Application and the K24 Web Platform (`https://k24.ai`). It explains how the "Connect via Browser" feature works and specifies the required URLs and redirects.

## 1. The Identified Issue
The "Connect via Browser" button was opening `http://localhost:3000/auth/desktop` instead of the production website.
*   **Cause:** The frontend code (`ConnectDevice.tsx`) relied on `process.env.NEXT_PUBLIC_APP_URL` which was undefined during the static build, falling back to `localhost`.
*   **Fix:** The code has been updated to default to `https://k24.ai` for production builds.

## 2. The Authentication Workflow

### Step 1: User Initiates Connection
*   **Action:** User clicks "Connect via Browser" in the Desktop App.
*   **Desktop App:** Generates a unique `device_id` (UUID) locally.
*   **Desktop App:** Opens the system default browser to:
    ```
    https://k24.ai/auth/desktop?device_id=<UUID>&app_version=1.0.0
    ```

### Step 2: Web Platform Authentication (Server-Side)
*   **Location:** `frontend/src/app/auth/desktop/page.tsx` (deployed on Vercel/Web).
*   **Logic:**
    1.  **Check Session:** Checks if the user is currently logged in to `k24.ai`.
    2.  **Redirect (if needed):** If not logged in, redirects to `/login` with a `next` parameter to return after login.
    3.  **Register Device:** Once logged in, the page calls the backend API endpoint `POST /api/devices/register` with:
        *   `device_id`: From URL parameters.
        *   `user_id`: From current web session.
    4.  **Generate License:** The backend generates a temporary `license_key` linked to this device and user.

### Step 3: Deep Link Callback
*   **Web Platform:** Redirects the browser to the custom protocol scheme:
    ```
    k24://auth/callback?license_key=<KEY>&user_id=<USER_ID>
    ```

### Step 4: Desktop App Validation
*   **Desktop App:** The Operating System recognizes `k24://` and wakes up the K24 Desktop App.
*   **Desktop App:** Parses the URL to extract `license_key` and `user_id`.
*   **Desktop App:** Verifies the license key with the local backend (Sidecar).
*   **Result:** Application authenticates and redirects to the Dashboard.

## 3. Required Configuration

### Desktop Application
*   **File:** `frontend/src/components/auth/ConnectDevice.tsx`
*   **Config:** Must point to `https://k24.ai` (Updated).
*   **Capabilities:** Must have `deep-link` plugin enabled and `k24` scheme registered (Verified).

### Web Platform (k24.ai)
*   **Route:** `/auth/desktop` must be accessible.
*   **Environment Variables:**
    *   `NEXT_PUBLIC_API_URL`: Must point to the production backend (e.g., `https://api.k24.ai` or same domain).

## 4. Troubleshooting
*   **"Link opens localhost":** The desktop app was built without the correct `NEXT_PUBLIC_USER` env var. (Fixed in code now).
*   **"Browser shows 404":** The web platform is not deployed or `/auth/desktop` route is missing.
*   **"Nothing happens after callback":** The `k24://` scheme might not be registered. Run the installer as Administrator to ensure registry keys are set.

## 5. Security Note
The `device_id` and `license_key` exchange ensures that only the specific device requesting access is granted a token. The license key should be short-lived (e.g., 5 minutes) and is exchanged for a permanent JWT/Refresh Token upon validation.
