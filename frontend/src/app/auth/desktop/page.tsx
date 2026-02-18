"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

function DesktopCallbackContent() {
    const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
    const [errorMessage, setErrorMessage] = useState("");
    const [licenseKey, setLicenseKey] = useState("");
    const [userId, setUserId] = useState("");
    const router = useRouter();
    const searchParams = useSearchParams();
    const supabase = createClient();

    useEffect(() => {
        const handleDesktopAuth = async () => {
            try {
                const deviceId = searchParams.get("device_id");
                const appVersion = searchParams.get("app_version");

                if (!deviceId) {
                    throw new Error("Missing device_id parameter");
                }

                // Check for local custom auth (Primary)
                let currentUserId = null;
                const localUserStr = localStorage.getItem("k24_user");
                if (localUserStr) {
                    try {
                        const localUser = JSON.parse(localUserStr);
                        if (localUser && localUser.id) {
                            currentUserId = localUser.id;
                        }
                    } catch (e) {
                        console.error("Error parsing local user:", e);
                    }
                }

                // Fallback to Supabase session if no local custom auth
                if (!currentUserId) {
                    const { data: { session }, error: authError } = await supabase.auth.getSession();
                    if (session?.user) {
                        currentUserId = session.user.id;
                    }
                }

                if (!currentUserId) {
                    // Redirect to login, preserving query params
                    const returnUrl = `/auth/desktop?device_id=${encodeURIComponent(deviceId)}&app_version=${encodeURIComponent(appVersion || "")}`;
                    router.push(`/login?next=${encodeURIComponent(returnUrl)}`);
                    return;
                }

                // Register device with cloud backend (this page runs in browser, not desktop)
                const cloudApiUrl = process.env.NEXT_PUBLIC_CLOUD_API_URL || "https://weare-production.up.railway.app";
                const response = await fetch(`${cloudApiUrl}/api/devices/register`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
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

                // Construct deep link
                const deepLink = `k24://auth/callback?license_key=${newLicenseKey}&user_id=${currentUserId}`;

                // Redirect back to desktop app
                window.location.href = deepLink;
                setStatus("success");

            } catch (err: any) {
                console.error("Desktop auth error:", err);
                setErrorMessage(err.message || "An unexpected error occurred");
                setStatus("error");
            }
        };

        handleDesktopAuth();
    }, [searchParams, router, supabase]);

    if (status === "error") {
        return (
            <div className="flex min-h-screen flex-col items-center justify-center p-4 bg-gray-50">
                <div className="bg-white p-8 rounded-lg shadow-md text-center max-w-md w-full">
                    <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100 mb-4">
                        <AlertCircle className="h-6 w-6 text-red-600" />
                    </div>
                    <h2 className="text-2xl font-bold text-gray-900 mb-2">Authentication Failed</h2>
                    <p className="text-gray-500 mb-6">{errorMessage}</p>
                    <Button onClick={() => window.location.reload()}>Try Again</Button>
                </div>
            </div>
        );
    }

    if (status === "success") {
        return (
            <div className="flex min-h-screen flex-col items-center justify-center p-4 bg-gray-50">
                <div className="bg-white p-8 rounded-lg shadow-md text-center max-w-md w-full">
                    <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-green-100 mb-4">
                        <CheckCircle2 className="h-6 w-6 text-green-600" />
                    </div>
                    <h1 className="text-2xl font-bold text-gray-900 mb-2">Successfully Connected!</h1>
                    <p className="text-gray-500 mb-6">You can now return to the K24 Desktop App.</p>

                    <div className="bg-slate-50 border border-slate-200 rounded-md p-4 mb-6 text-left">
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Manual Entry Details</p>
                        <div className="space-y-3">
                            <div>
                                <label className="text-xs text-slate-400 block mb-1">License Key</label>
                                <code className="block bg-white p-2 rounded border border-slate-200 text-sm font-mono select-all">
                                    {licenseKey}
                                </code>
                            </div>
                        </div>
                        <p className="text-[10px] text-slate-400 mt-2 text-center">
                            Copy this key if the app didn't open automatically.
                        </p>
                    </div>

                    <div className="text-sm text-gray-400">
                        <a href={`k24://auth/callback?license_key=${licenseKey}&user_id=${userId}`} className="text-blue-600 hover:underline font-medium">
                            Try opening Desktop App again
                        </a>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="flex min-h-screen flex-col items-center justify-center p-4 bg-gray-50">
            <div className="text-center">
                <Loader2 className="h-10 w-10 animate-spin text-blue-600 mx-auto mb-4" />
                <h2 className="text-xl font-semibold text-gray-900">Connecting Device...</h2>
                <p className="text-gray-500 mt-2">Please wait while we set up your secure connection.</p>
            </div>
        </div>
    );
}

export default function DesktopAuthCallback() {
    return (
        <Suspense fallback={
            <div className="flex min-h-screen items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
            </div>
        }>
            <DesktopCallbackContent />
        </Suspense>
    );
}
