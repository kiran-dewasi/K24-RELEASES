"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
    LayoutDashboard,
    BookOpen,
    FileText,
    PieChart,
    Settings,
    MessageSquare,
    LogOut,
    Sparkles
} from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useUser } from "@/contexts/UserContext";

interface NavItem {
    name: string;
    href: string;
    icon: any;
    special?: boolean;
}

const navGroups: { label: string; items: NavItem[] }[] = [
    {
        label: "Workspace",
        items: [
            { name: "Dashboard", href: "/", icon: LayoutDashboard },
            { name: "Daybook", href: "/daybook", icon: BookOpen },
            { name: "Invoices", href: "/invoices", icon: FileText },
            { name: "Reports", href: "/reports", icon: PieChart },
        ]
    },
    {
        label: "Intelligence",
        items: [
            { name: "KITTU Chat", href: "/chat", icon: MessageSquare, special: true },
        ]
    }
];

/** Extract initials from a full name, e.g. "Kiran Dewasi" → "KD" */
function getInitials(name: string | undefined | null): string {
    if (!name) return "??";
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    return name.slice(0, 2).toUpperCase();
}

/** Format role for display */
function formatRole(role: string | undefined | null): string {
    if (!role) return "";
    // Capitalize first letter
    return role.charAt(0).toUpperCase() + role.slice(1);
}

export default function Sidebar() {
    const pathname = usePathname();
    const { user, loading } = useUser();

    return (
        <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r bg-[#FBFBFB] flex flex-col justify-between transition-transform">

            {/* Top Section */}
            <div>
                {/* Brand Area */}
                <div className="flex h-16 items-center px-6 border-b border-sidebar-border/50 bg-[#FBFBFB]">
                    <div className="flex items-center gap-2 font-bold text-xl tracking-tight text-foreground">
                        <div className="h-8 w-8 rounded-lg bg-primary text-primary-foreground flex items-center justify-center">
                            K
                        </div>
                        <span>K24.ai</span>
                    </div>
                </div>

                {/* Navigation */}
                <nav className="flex-1 space-y-6 px-3 py-6">
                    {navGroups.map((group, idx) => (
                        <div key={idx} className="space-y-2">
                            <h4 className="px-4 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                                {group.label}
                            </h4>

                            <div className="space-y-1">
                                {group.items.map((item) => {
                                    const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
                                    const Icon = item.icon;

                                    return (
                                        <Link
                                            key={item.href}
                                            href={item.href}
                                            className={cn(
                                                "group flex items-center gap-3 rounded-md px-4 py-2 text-sm font-medium transition-all duration-200 relative overflow-hidden",
                                                isActive
                                                    ? "bg-primary/10 text-primary"
                                                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                                            )}
                                        >
                                            {isActive && (
                                                <span className="absolute left-0 top-0 bottom-0 w-1 bg-primary rounded-r-full" />
                                            )}
                                            <Icon className={cn("h-4 w-4", item.special && "text-amber-500 fill-amber-500/20")} />
                                            <span>{item.name}</span>
                                            {item.special && (
                                                <Sparkles className="ml-auto h-3 w-3 text-amber-500 animate-pulse" />
                                            )}
                                        </Link>
                                    );
                                })}
                            </div>
                        </div>
                    ))}
                </nav>
            </div>

            {/* Bottom Section */}
            <div className="p-4 border-t border-sidebar-border/50 bg-[#FBFBFB]">
                <div className="space-y-1">
                    <Link
                        href="/settings"
                        className={cn(
                            "group flex items-center gap-3 rounded-md px-4 py-2 text-sm font-medium transition-colors text-muted-foreground hover:bg-muted hover:text-foreground",
                            pathname.startsWith("/settings") && "bg-muted text-foreground"
                        )}
                    >
                        <Settings className="h-4 w-4" />
                        <span>Settings</span>
                    </Link>

                    {/* Sign Out - only show when user is logged in */}
                    {user && (
                        <button
                            onClick={() => {
                                if (window.confirm("Are you sure you want to sign out?")) {
                                    localStorage.removeItem("k24_license_key");
                                    localStorage.removeItem("k24_device_id");
                                    localStorage.removeItem("k24_tenant_id");
                                    localStorage.removeItem("k24_user_id");
                                    localStorage.removeItem("k24_token");
                                    localStorage.removeItem("k24_user");
                                    window.location.href = "/login";
                                }
                            }}
                            className="w-full group flex items-center gap-3 rounded-md px-4 py-2 text-sm font-medium transition-colors text-muted-foreground hover:bg-destructive/10 hover:text-destructive text-left"
                        >
                            <LogOut className="h-4 w-4" />
                            <span>Sign Out</span>
                        </button>
                    )}

                    {/* User Profile */}
                    <div className="pt-4 flex items-center gap-3 px-4">
                        {loading ? (
                            <>
                                <div className="h-8 w-8 rounded-lg bg-muted animate-pulse" />
                                <div className="flex flex-col gap-1">
                                    <div className="h-3 w-20 bg-muted animate-pulse rounded" />
                                    <div className="h-2 w-12 bg-muted animate-pulse rounded" />
                                </div>
                            </>
                        ) : user ? (
                            <>
                                <Avatar className="h-8 w-8 rounded-lg">
                                    <AvatarFallback className="rounded-lg bg-orange-100 text-orange-700 font-bold">
                                        {getInitials(user.full_name)}
                                    </AvatarFallback>
                                </Avatar>
                                <div className="flex flex-col">
                                    <span className="text-xs font-semibold text-foreground">
                                        {user.full_name}
                                    </span>
                                    <span className="text-[10px] text-muted-foreground">
                                        {formatRole(user.role)}
                                    </span>
                                </div>
                            </>
                        ) : null}
                    </div>
                </div>
            </div>

        </aside>
    );
}
