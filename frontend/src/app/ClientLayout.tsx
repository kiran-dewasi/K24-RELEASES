"use client";

import { usePathname } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import Navbar from "@/components/Navbar";

import { Toaster } from "@/components/ui/toaster";
import { UpdateNotification } from "@/components/UpdateNotification";
import { UserProvider } from "@/contexts/UserContext";
import AuthGuard from "@/components/AuthGuard";

export default function ClientLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const isPublicPage = ["/login", "/signup", "/onboarding", "/forgot-password", "/reset-password", "/auth"].some(path => pathname.startsWith(path));

    // Public pages: no auth required, no sidebar
    if (isPublicPage) {
        return <>{children}<Toaster /></>;
    }

    // Authenticated pages: UserProvider → AuthGuard → Layout
    return (
        <UserProvider>
            <AuthGuard>
                <div className="flex bg-gray-50 min-h-screen">
                    <Sidebar />
                    <div className="flex-1 ml-64 flex flex-col h-screen">
                        <Navbar />
                        <main className="flex-1 p-8 overflow-y-auto">
                            <div className="max-w-7xl mx-auto">
                                {children}
                            </div>
                        </main>
                    </div>
                    <Toaster />
                    <UpdateNotification />
                </div>
            </AuthGuard>
        </UserProvider>
    );
}
