# K24 Web Authentication Specification
## Overview
This document describes the required implementation for the **K24 Web Authentication Page** (`https://k24.ai/auth/desktop`).
This page is responsible for authenticating a user on the web and securely transferring a License Key to the Desktop App via Deep Link.

## 1. Frontend Page (`/auth/desktop/page.tsx`)
**Path:** `frontend/src/app/auth/desktop/page.tsx`
**Framework:** Next.js (App Router)

### Logic Flow
1. **Receive Parameters:** Extract `device_id` and `app_version` from URL Query Params.
2. **Check Session:** Verify if the user is logged in (via Supabase Auth or Local Storage).
   - If **Not Logged In**: Redirect to `/login` with a `returnUrl` pointing back to this page.
3. **Register Device:** Call the Backend API (`POST /api/devices/register`) with `device_id` and `user_id`.
4. **Receive License:** The API returns a `license_key`.
5. **Redirect to Desktop:** Redirect the browser to `k24://auth/callback?license_key=...&user_id=...`.

### Code Implementation
Copy this code into `src/app/auth/desktop/page.tsx`:

```tsx
"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClientComponentClient } from "@supabase/auth-helpers-nextjs";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";

function DesktopCallbackContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const supabase = createClientComponentClient();

    const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
    const [errorMessage, setErrorMessage] = useState("");
    const [licenseKey, setLicenseKey] = useState("");
    const [userId, setUserId] = useState("");

    useEffect(() => {
        handleDesktopAuth();
    }, []);

    const handleDesktopAuth = async () => {
        try {
            const deviceId = searchParams.get("device_id");
            const appVersion = searchParams.get("app_version");

            if (!deviceId) {
                throw new Error("Missing device_id parameter");
            }

            // 1. Get Current User
            const { data: { session } } = await supabase.auth.getSession();
            let currentUserId = session?.user?.id;

            // Optional: Support custom local auth if not using Supabase
            if (!currentUserId) {
                 const localUser = localStorage.getItem("k24_user");
                 if (localUser) currentUserId = JSON.parse(localUser).id;
            }

            // 2. Redirect to Login if needed
            if (!currentUserId) {
                const returnUrl = `/auth/desktop?device_id=${encodeURIComponent(deviceId)}&app_version=${encodeURIComponent(appVersion || "")}`;
                router.push(`/login?next=${encodeURIComponent(returnUrl)}`);
                return;
            }

            // 3. Register Device with Backend API
            // Note: Ensure NEXT_PUBLIC_API_URL is set in your .env
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://api.k24.ai"; 
            
            const response = await fetch(`${apiUrl}/api/devices/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    device_id: deviceId,
                    user_id: currentUserId,
                    app_version: appVersion,
                }),
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || "Failed to register device");
            }

            const data = await response.json();
            const newLicenseKey = data.license_key;

            setLicenseKey(newLicenseKey);
            setUserId(currentUserId);
            setStatus("success");

            // 4. Redirect to Desktop App via Deep Link
            const deepLink = `k24://auth/callback?license_key=${newLicenseKey}&user_id=${currentUserId}`;
            window.location.href = deepLink;

        } catch (err: any) {
            console.error("Auth error:", err);
            setErrorMessage(err.message || "An unexpected error occurred");
            setStatus("error");
        }
    };

    if (status === "loading") {
        return (
            <div className="flex h-screen items-center justify-center bg-gray-50 flex-col gap-4">
                <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
                <p className="text-gray-500">Authenticating Device...</p>
            </div>
        );
    }

    if (status === "error") {
        return (
            <div className="flex h-screen items-center justify-center bg-gray-50">
                <div className="bg-white p-8 rounded-xl shadow-lg max-w-md text-center">
                    <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
                    <h2 className="text-xl font-bold text-gray-900">Authentication Failed</h2>
                    <p className="text-gray-500 mt-2">{errorMessage}</p>
                    <button onClick={() => window.location.reload()} className="mt-6 px-4 py-2 bg-gray-100 rounded hover:bg-gray-200">
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="flex min-h-screen flex-col items-center justify-center p-4 bg-gray-50">
            <div className="bg-white p-8 rounded-xl shadow-lg text-center max-w-md w-full animate-in fade-in zoom-in">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100 mb-6">
                    <CheckCircle2 className="h-8 w-8 text-green-600" />
                </div>
                <h1 className="text-2xl font-bold text-gray-900 mb-2">Successfully Connected!</h1>
                <p className="text-gray-500 mb-6">Redirecting you back to K24 Desktop...</p>

                <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 mb-6 text-left">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Manual Entry Code</p>
                    <code className="block bg-white p-3 rounded border border-slate-200 text-sm font-mono select-all text-center font-bold tracking-widest">
                        {licenseKey}
                    </code>
                    <p className="text-[10px] text-slate-400 mt-2 text-center">
                        Copy this if the app doesn't open automatically.
                    </p>
                </div>

                <a href={`k24://auth/callback?license_key=${licenseKey}&user_id=${userId}`} 
                   className="block w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors">
                    Open Desktop App
                </a>
            </div>
        </div>
    );
}

export default function DesktopAuthCallback() {
    return (
        <Suspense fallback={<div className="h-screen bg-gray-50" />}>
            <DesktopCallbackContent />
        </Suspense>
    );
}
```

## 2. Backend Requirements (Production)
Your Production Backend (`https://api.k24.ai`) must implement the device registration endpoint.

**Endpoint:** `POST /api/devices/register`
**Payload:**
```json
{
  "device_id": "string",
  "user_id": "string",
  "app_version": "string"
}
```

**Implementation Guide (FastAPI/Python):**
Ensure your `routers/devices.py` exists on the production server and is wired in `main.py`.
Also ensure the `DeviceLicense` table exists in your Production Database.

## 3. Environment Variables
Make sure your Production Website (`k24.ai`) has:
- `NEXT_PUBLIC_API_URL`: pointing to your production backend (e.g., `https://api.k24.ai`).
- `NEXT_PUBLIC_SUPABASE_URL`: (If using Supabase).
