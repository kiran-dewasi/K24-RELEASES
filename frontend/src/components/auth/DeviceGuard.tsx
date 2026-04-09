// DEV ONLY: bypass device licensing in development mode to unblock auth/dashboard work.
"use client";

import { useEffect, useState } from "react";
import ConnectDevice from "./ConnectDevice";
import { Loader2 } from "lucide-react";
import { apiRequest } from "@/lib/api";

export default function DeviceGuard({ children }: { children: React.ReactNode }) {
    const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);

    useEffect(() => {
        // ─── DEV BYPASS ───────────────────────────────────────────────────────────
        // In development mode, skip ALL license checks so the auth/dashboard flow
        // is never blocked. The ConnectDevice / license gate is still intact for
        // production builds (NODE_ENV === 'production').
        if (process.env.NODE_ENV === "development") {
            console.log("[DeviceGuard] DEV MODE — license gate bypassed, setting isAuthorized = true");
            setIsAuthorized(true);
            return; // Skip license check, API calls, and periodic timer entirely
        }
        // ─── END DEV BYPASS ───────────────────────────────────────────────────────

        const checkLicense = async () => {
            console.log("[DeviceGuard] Starting license check...");

            const license = localStorage.getItem("k24_license_key");
            console.log("[DeviceGuard] License key:", license);

            if (license) {
                // Optional: Validate on startup
                // const isValid = await validate(license);
                console.log("[DeviceGuard] Set isAuthorized = TRUE (has license)");
                setIsAuthorized(true);
            } else {
                console.log("[DeviceGuard] Set isAuthorized = FALSE (no license)");
                setIsAuthorized(false);
            }
        };

        checkLicense();

        // Periodic Validation (Every 5 minutes) — production only
        const interval = setInterval(async () => {
            const license = localStorage.getItem("k24_license_key");
            const deviceId = localStorage.getItem("k24_device_id");

            if (!license || !deviceId) return;

            try {
                // Use apiRequest for secure routing (Cloud)
                const data = await apiRequest(
                    `/api/devices/validate?license_key=${license}&device_id=${deviceId}`,
                    "GET"
                );

                if (data && !data.valid) {
                    console.warn("License validation failed:", data.reason);
                    localStorage.removeItem("k24_license_key");
                    setIsAuthorized(false);
                }
            } catch (e) {
                console.error("Background validation error:", e);
            }
        }, 5 * 60 * 1000);

        return () => clearInterval(interval);
    }, []);

    // DEV ONLY: Keyboard shortcut to reset activation state (Ctrl+Shift+R)
    // This is a development convenience tool for testing activation flows
    // Only active when NODE_ENV === 'development'
    // Production builds will ignore this keyboard shortcut entirely
    useEffect(() => {
        const handleKeyPress = (e: KeyboardEvent) => {
            // Strict guard: only in development mode
            if (process.env.NODE_ENV !== "development") return;

            // Ctrl+Shift+R to reset activation
            if (e.ctrlKey && e.shiftKey && e.key === "R") {
                e.preventDefault();
                console.log("[DEV] Resetting device activation state...");

                // Clear all activation-related localStorage
                localStorage.removeItem("k24_license_key");
                localStorage.removeItem("k24_device_id");
                localStorage.removeItem("k24_user_id");
                localStorage.removeItem("k24_user");

                // Alert user and reload
                alert("✅ Device activation reset! Showing ConnectDevice screen.");
                window.location.reload();
            }
        };

        window.addEventListener("keydown", handleKeyPress);
        return () => window.removeEventListener("keydown", handleKeyPress);
    }, []);

    console.log("[DeviceGuard] RENDER - isAuthorized state:", isAuthorized);

    if (isAuthorized === null) {
        return (
            <div className="flex h-screen items-center justify-center bg-gray-50">
                <div className="flex flex-col items-center gap-2">
                    <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
                    <p className="text-sm text-gray-400">Verifying Device License...</p>
                </div>
            </div>
        );
    }

    if (!isAuthorized) {
        console.log("[DeviceGuard] RENDER - Rendering ConnectDevice with fullscreen overlay");
        return <ConnectDevice onAuthenticated={() => setIsAuthorized(true)} />;
    }

    console.log("[DeviceGuard] RENDER - Rendering Children (Dashboard)");
    return <>{children}</>;
}
