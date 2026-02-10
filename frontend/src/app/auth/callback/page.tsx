"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";

/**
 * Auth Callback Page Content
 * Handles Supabase authentication callbacks.
 */
function AuthCallbackContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [message, setMessage] = useState("Processing authentication...");

    useEffect(() => {
        const handleCallback = async () => {
            // Check for different auth flow types
            const type = searchParams.get("type");
            const accessToken = searchParams.get("access_token");
            const refreshToken = searchParams.get("refresh_token");
            const error = searchParams.get("error");
            const errorDescription = searchParams.get("error_description");

            // Handle errors
            if (error) {
                setMessage(`Error: ${errorDescription || error}`);
                setTimeout(() => router.push("/login"), 3000);
                return;
            }

            // Handle password recovery
            if (type === "recovery" && accessToken) {
                // Redirect to reset password page with token
                router.push(`/reset-password?access_token=${accessToken}`);
                return;
            }

            // Handle email verification
            if (type === "signup" || type === "email_change") {
                setMessage("Email verified! Redirecting to login...");
                setTimeout(() => router.push("/login"), 2000);
                return;
            }

            // Handle OAuth or magic link login
            if (accessToken) {
                // Store tokens and redirect to dashboard
                // Note: In production, you might want to exchange this for a backend session
                localStorage.setItem("k24_supabase_token", accessToken);
                if (refreshToken) {
                    localStorage.setItem("k24_supabase_refresh", refreshToken);
                }

                setMessage("Login successful! Redirecting...");
                setTimeout(() => router.push("/daybook"), 1000);
                return;
            }

            // Default: unknown callback, go to login
            setMessage("Unknown callback. Redirecting to login...");
            setTimeout(() => router.push("/login"), 2000);
        };

        handleCallback();
    }, [router, searchParams]);

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center p-4">
            <div className="text-center">
                <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
                <p className="text-gray-600">{message}</p>
            </div>
        </div>
    );
}

export default function AuthCallbackPage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen flex items-center justify-center p-4">
                <Loader2 className="w-12 h-12 text-blue-600 animate-spin" />
            </div>
        }>
            <AuthCallbackContent />
        </Suspense>
    );
}
