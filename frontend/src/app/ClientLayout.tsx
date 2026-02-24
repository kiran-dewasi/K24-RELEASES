"use client";

import { usePathname } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import Navbar from "@/components/Navbar";
import { Toaster } from "@/components/ui/toaster";
import { UpdateNotification } from "@/components/UpdateNotification";
import { UserProvider } from "@/contexts/UserContext";
import { SidebarProvider, useSidebar } from "@/contexts/SidebarContext";
import { ChatProvider } from "@/contexts/ChatContext";
import AuthGuard from "@/components/AuthGuard";

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
            <UpdateNotification />
        </div>
    );
}

export default function ClientLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const isPublicPage = ["/login", "/signup", "/onboarding", "/forgot-password", "/reset-password", "/auth"]
        .some(p => pathname.startsWith(p));

    if (isPublicPage) return <>{children}<Toaster /></>;

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
