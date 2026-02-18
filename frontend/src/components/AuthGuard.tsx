"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useUser } from "@/contexts/UserContext";
import { Loader2 } from "lucide-react";

/**
 * AuthGuard wraps authenticated routes.
 * - Shows a full-screen loader while user data is being fetched
 * - Redirects to /login if no valid user after loading completes
 * - Only renders children when a valid user exists
 */
export default function AuthGuard({ children }: { children: React.ReactNode }) {
    const { user, loading } = useUser();
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
        // Once loading is done and there's no user, redirect to login
        if (!loading && !user) {
            router.replace("/login");
        }
    }, [loading, user, router]);

    // Still loading – show a clean full-screen spinner
    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen w-full bg-gray-50">
                <div className="flex flex-col items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-primary text-primary-foreground flex items-center justify-center font-bold text-lg">
                        K
                    </div>
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">Loading K24…</p>
                </div>
            </div>
        );
    }

    // No user after loading → will redirect via useEffect, render nothing meanwhile
    if (!user) {
        return null;
    }

    // User exists → render the actual page
    return <>{children}</>;
}
