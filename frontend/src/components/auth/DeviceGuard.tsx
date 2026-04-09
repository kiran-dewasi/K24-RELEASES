// PASSTHROUGH: DeviceGuard is preserved as a wrapper but device registration
// is no longer required. All authenticated users go directly to the dashboard.
// The ConnectDevice screen is permanently bypassed for all environments.
"use client";

import { useEffect, useState } from "react";
// ConnectDevice and apiRequest imports kept to avoid breaking the module graph
// but are no longer invoked at runtime.
import ConnectDevice from "./ConnectDevice";
import { apiRequest } from "@/lib/api";

export default function DeviceGuard({ children }: { children: React.ReactNode }) {
    const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);

    useEffect(() => {
        // PASSTHROUGH: Always authorize. No license check, no API call, no localStorage read.
        // Every logged-in user reaches the dashboard directly.
        console.log("[DeviceGuard] PASSTHROUGH — skipping all license checks, setting isAuthorized = true");
        setIsAuthorized(true);
    }, []);

    // isAuthorized starts as null (component just mounted) — resolve it immediately above.
    // While null, render nothing (flash-free mount).
    if (isAuthorized === null) {
        return null;
    }

    // isAuthorized is always true — this branch is unreachable in normal operation.
    // Kept for structural integrity; ConnectDevice is never rendered.
    if (!isAuthorized) {
        return <ConnectDevice onAuthenticated={() => setIsAuthorized(true)} />;
    }

    console.log("[DeviceGuard] RENDER - Rendering Children (Dashboard)");
    return <>{children}</>;
}
