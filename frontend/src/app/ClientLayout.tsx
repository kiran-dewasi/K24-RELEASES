"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import Navbar from "@/components/Navbar";
import { Toaster } from "@/components/ui/toaster";
import { UserProvider } from "@/contexts/UserContext";
import { SidebarProvider, useSidebar } from "@/contexts/SidebarContext";
import { ChatProvider } from "@/contexts/ChatContext";
import AuthGuard from "@/components/AuthGuard";
import TrialBanner from "@/components/TrialBanner";
import { initBackendPort } from "@/lib/api";

function InnerLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const { collapsed } = useSidebar();

    // Chat page: full-height workbench — no navbar, no padding, no max-width
    const isFullWorkbench = pathname.startsWith("/chat");

    return (
        <div className="flex bg-[#F8F9FC] min-h-screen">
            <Sidebar />
            <div
                className="flex flex-col h-screen overflow-hidden transition-[margin-left] duration-300 ease-in-out flex-1"
                style={{ marginLeft: collapsed ? "60px" : "260px" }}
            >
                {/* Navbar is hidden for the full-workbench chat page */}
                {!isFullWorkbench && <Navbar />}

                {/* Trial banner — between Navbar and page content, hidden on chat workbench */}
                {!isFullWorkbench && <TrialBanner />}

                {isFullWorkbench ? (
                    // Full workbench — takes full height, no navbar overhead
                    <div className="flex-1 overflow-hidden">
                        {children}
                    </div>
                ) : (
                    <main className="flex-1 p-8 overflow-y-auto">
                        <div className="max-w-7xl mx-auto">
                            {children}
                        </div>
                    </main>
                )}
            </div>
            <Toaster />
        </div>
    );
}

export default function ClientLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();

    // Resolve the Rust sidecar's dynamic port once on mount and cache it
    // so all apiRequest() calls use the correct port instead of hardcoded 8001.
    // Also listens for `backend_ready` event (emitted by Rust after sidecar starts)
    // to handle the race where the port isn't stored yet on first mount.
    useEffect(() => {
        // Attempt immediately — may still be early (before Rust finishes start_backend)
        initBackendPort();

        let unlisten: (() => void) | undefined;
        (async () => {
            if (typeof window !== "undefined" && ("__TAURI_INTERNALS__" in window || "__TAURI__" in window)) {
                try {
                    const { listen } = await import("@tauri-apps/api/event");
                    unlisten = await listen("backend_ready", () => {
                        // Rust just finished start_backend — re-fetch the port now it's stored
                        initBackendPort();
                    });
                } catch {
                    // Not in Tauri — ignore
                }
            }
        })();

        return () => { unlisten?.(); };
    }, []);

    const isPublicPage = ["/login", "/signup", "/onboarding", "/forgot-password", "/reset-password", "/auth"]
        .some(p => pathname.startsWith(p));

    // Admin portal is developer-only — bypasses user auth entirely
    const isAdminPage = pathname.startsWith("/admin");

    // Public marketing pages — no auth, no sidebar
    const isPricingPage = pathname.startsWith("/pricing") || pathname.startsWith("/subscribe");

    if (isPublicPage || isAdminPage || isPricingPage) return <>{children}<Toaster /></>;

    return (
        <UserProvider>
            <SidebarProvider>
                <ChatProvider>
                    <AuthGuard>
                        <InnerLayout>{children}</InnerLayout>
                    </AuthGuard>
                </ChatProvider>
            </SidebarProvider>
        </UserProvider>
    );
}
