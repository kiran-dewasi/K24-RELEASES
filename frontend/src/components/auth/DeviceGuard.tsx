"use client";

import { useEffect, useState } from "react";
import ConnectDevice from "./ConnectDevice";
import { Loader2 } from "lucide-react";

export default function DeviceGuard({ children }: { children: React.ReactNode }) {
    const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);

    useEffect(() => {
        const checkLicense = async () => {
            const license = localStorage.getItem("k24_license_key");

            if (license) {
                // Optional: Validate on startup
                // const isValid = await validate(license); 
                setIsAuthorized(true);
            } else {
                setIsAuthorized(false);
            }
        };

        checkLicense();

        // Periodic Validation (Every 5 minutes)
        const interval = setInterval(async () => {
            const license = localStorage.getItem("k24_license_key");
            const deviceId = localStorage.getItem("k24_device_id");

            if (!license || !deviceId) return;

            try {
                const response = await fetch(`http://localhost:8000/api/devices/validate?license_key=${license}&device_id=${deviceId}`);
                if (!response.ok) return;

                const data = await response.json();

                if (!data.valid) {
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
        return <ConnectDevice onAuthenticated={() => setIsAuthorized(true)} />;
    }

    return <>{children}</>;
}
