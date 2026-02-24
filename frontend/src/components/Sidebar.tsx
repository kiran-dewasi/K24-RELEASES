"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import {
    LayoutDashboard, BookOpen, FileText, PieChart,
    Settings, MessageSquare, LogOut, Sparkles,
    ChevronLeft, ChevronRight, Plus, Search,
    Trash2, MessagesSquare,
} from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useUser } from "@/contexts/UserContext";
import { useSidebar } from "@/contexts/SidebarContext";
import { useChat } from "@/contexts/ChatContext";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getInitials(name: string | undefined | null) {
    if (!name) return "??";
    const p = name.trim().split(/\s+/);
    return p.length >= 2 ? (p[0][0] + p[p.length - 1][0]).toUpperCase() : name.slice(0, 2).toUpperCase();
}

function fmtRelative(iso: string) {
    const diff = Date.now() - new Date(iso).getTime();
    if (diff < 60_000) return "just now";
    if (diff < 3_600_000) return Math.floor(diff / 60_000) + "m ago";
    if (diff < 86_400_000) return Math.floor(diff / 3_600_000) + "h ago";
    return new Date(iso).toLocaleDateString([], { month: "short", day: "numeric" });
}

/** Pure-CSS tooltip shown only in collapsed mode */
function Tip({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div className="relative group/tip w-full flex justify-center">
            {children}
            <div className="
                pointer-events-none absolute left-full top-1/2 -translate-y-1/2 ml-3
                bg-slate-800 text-white text-xs font-medium px-2.5 py-1 rounded-lg whitespace-nowrap
                opacity-0 group-hover/tip:opacity-100 -translate-x-1 group-hover/tip:translate-x-0
                transition-all duration-150 z-[100] shadow-lg
            ">
                {label}
                <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-slate-800" />
            </div>
        </div>
    );
}

// ─── Nav items config ─────────────────────────────────────────────────────────

const NAV = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Daybook", href: "/daybook", icon: BookOpen },
    { name: "Invoices", href: "/invoices", icon: FileText },
    { name: "Reports", href: "/reports", icon: PieChart },
];

// ─── NavLink ──────────────────────────────────────────────────────────────────

function NavLink({
    href, icon: Icon, label, active, collapsed, sparkle = false,
}: {
    href: string; icon: any; label: string; active: boolean; collapsed: boolean; sparkle?: boolean;
}) {
    const el = (
        <Link href={href} className={cn(
            "group relative flex items-center gap-3 rounded-xl text-sm font-medium transition-all duration-150 w-full",
            collapsed ? "justify-center h-10 px-0" : "px-3.5 py-2.5",
            active ? "bg-indigo-50 text-indigo-700" : "text-slate-500 hover:bg-slate-100 hover:text-slate-800"
        )}>
            {active && !collapsed && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-0.5 bg-indigo-500 rounded-r-full" />
            )}
            <Icon className={cn("h-[18px] w-[18px] shrink-0", active ? "text-indigo-600" : sparkle ? "text-amber-500" : "")} />
            {!collapsed && (
                <>
                    <span>{label}</span>
                    {sparkle && <Sparkles className="ml-auto h-3 w-3 text-amber-400" />}
                </>
            )}
        </Link>
    );
    return collapsed ? <Tip label={label}>{el}</Tip> : el;
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

export default function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const { user, loading } = useUser();
    const { collapsed, toggle } = useSidebar();
    const chat = useChat();

    const isOnChat = pathname.startsWith("/chat");

    // ── handlers ───────────────────────────────────────────────────────────
    const handleNewChat = () => {
        const id = chat.startNewThread();
        router.push("/chat");
        // Signal KittuChat to clear messages
        window.dispatchEvent(new CustomEvent("k24_new_thread", { detail: { id } }));
    };

    const handleSelectThread = (id: string) => {
        chat.setActiveThreadId(id);
        router.push("/chat");
        window.dispatchEvent(new CustomEvent("k24_select_thread", { detail: { id } }));
    };

    const handleDeleteThread = (e: React.MouseEvent, id: string) => {
        e.stopPropagation();
        chat.deleteThread(id);
        if (chat.activeThreadId === id) handleNewChat();
    };

    const handleSignOut = () => {
        if (window.confirm("Sign out?")) {
            ["k24_license_key", "k24_device_id", "k24_tenant_id", "k24_user_id", "k24_token", "k24_user"]
                .forEach(k => localStorage.removeItem(k));
            window.location.href = "/login";
        }
    };

    // ── render ─────────────────────────────────────────────────────────────
    return (
        <aside className={cn(
            "fixed left-0 top-0 z-40 h-screen border-r border-slate-200 bg-[#F8F9FC]",
            "flex flex-col overflow-hidden",
            "transition-[width] duration-300 ease-in-out",
            collapsed ? "w-[60px]" : "w-[260px]"
        )}>

            {/* ── Header: Logo + toggle ─────────────────────────────────── */}
            <div className={cn(
                "flex h-14 shrink-0 items-center border-b border-slate-200/80 relative",
                collapsed ? "justify-center" : "px-4 justify-between"
            )}>
                <Link href="/" className="flex items-center gap-2.5 font-bold tracking-tight shrink-0">
                    <div className="h-7 w-7 rounded-lg bg-indigo-600 text-white flex items-center justify-center text-sm font-bold shrink-0 shadow-sm shadow-indigo-300">
                        K
                    </div>
                    {!collapsed && <span className="text-[15px] font-semibold text-slate-800">K24.ai</span>}
                </Link>

                {/* Edge toggle button */}
                <button
                    onClick={toggle}
                    className="absolute -right-3 top-1/2 -translate-y-1/2 z-50 h-6 w-6 rounded-full border border-slate-300 bg-white shadow-sm text-slate-400 hover:text-slate-700 hover:border-slate-400 hover:shadow-md transition-all duration-200 flex items-center justify-center"
                    aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
                >
                    {collapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronLeft className="h-3 w-3" />}
                </button>
            </div>

            {/* ── New Chat button (always visible, prominent on chat page) ── */}
            <div className={cn("shrink-0 pt-3 pb-1", collapsed ? "px-2" : "px-3")}>
                {collapsed ? (
                    <Tip label="New Chat">
                        <button onClick={handleNewChat}
                            className="w-full h-9 rounded-xl bg-indigo-600 hover:bg-indigo-700 flex items-center justify-center text-white transition-colors shadow-sm shadow-indigo-200">
                            <Plus className="h-4 w-4" />
                        </button>
                    </Tip>
                ) : (
                    <button onClick={handleNewChat}
                        className="w-full h-9 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-[13px] font-semibold flex items-center justify-center gap-2 transition-colors shadow-sm shadow-indigo-200">
                        <Plus className="h-3.5 w-3.5" />
                        New Chat
                    </button>
                )}
            </div>

            {/* ── Main nav ─────────────────────────────────────────────────── */}
            <nav className={cn("shrink-0 pt-3 pb-1 space-y-0.5", collapsed ? "px-2" : "px-3")}>
                {!collapsed && (
                    <p className="px-3.5 text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-1.5">Workspace</p>
                )}
                {NAV.map(({ name, href, icon }) => (
                    <NavLink key={href} href={href} icon={icon} label={name} collapsed={collapsed}
                        active={href === "/" ? pathname === "/" : pathname.startsWith(href)}
                    />
                ))}

                <div className="pt-1">
                    {!collapsed && (
                        <p className="px-3.5 pt-1 text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-1.5">Intelligence</p>
                    )}
                    {collapsed && <div className="h-px bg-slate-200/80 my-1.5 mx-1" />}
                    <NavLink href="/chat" icon={MessageSquare} label="KITTU Chat" collapsed={collapsed}
                        active={isOnChat} sparkle
                    />
                </div>
            </nav>

            {/* ── Thread history — fills remaining space on /chat ───────── */}
            {isOnChat && !collapsed && (
                <div className="flex flex-col flex-1 overflow-hidden min-h-0 px-3 pt-1 pb-1">
                    {/* Divider */}
                    <div className="flex items-center gap-2 py-2">
                        <MessagesSquare className="h-3 w-3 text-slate-400 shrink-0" />
                        <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">Recent chats</span>
                    </div>

                    {/* Thread list — scrollable */}
                    <div className="flex-1 overflow-y-auto space-y-0.5 pr-0.5"
                        style={{ scrollbarWidth: "thin", scrollbarColor: "#e2e8f0 transparent" }}>
                        {chat.threads.length === 0 ? (
                            <div className="flex flex-col items-center justify-center h-20 gap-2 text-center">
                                <MessagesSquare className="h-6 w-6 text-slate-200" />
                                <p className="text-[11px] text-slate-400">No chats yet</p>
                            </div>
                        ) : (
                            chat.threads.map(thread => {
                                const isActive = thread.id === chat.activeThreadId;
                                return (
                                    <div key={thread.id}
                                        onClick={() => handleSelectThread(thread.id)}
                                        className={cn(
                                            "group relative rounded-lg px-3 py-2 cursor-pointer transition-all duration-150",
                                            isActive
                                                ? "bg-indigo-50 border border-indigo-100"
                                                : "hover:bg-white border border-transparent hover:border-slate-200"
                                        )}
                                    >
                                        {isActive && (
                                            <span className="absolute left-0 top-2 bottom-2 w-0.5 bg-indigo-500 rounded-r-full" />
                                        )}
                                        <div className="flex items-start justify-between gap-1.5">
                                            <p className={cn(
                                                "text-[12px] font-medium truncate leading-tight",
                                                isActive ? "text-indigo-700" : "text-slate-600"
                                            )}>
                                                {thread.title}
                                            </p>
                                            <div className="flex items-center gap-0.5 shrink-0">
                                                <span className="text-[10px] text-slate-400">
                                                    {fmtRelative(thread.updatedAt)}
                                                </span>
                                                <button
                                                    onClick={e => handleDeleteThread(e, thread.id)}
                                                    className="opacity-0 group-hover:opacity-100 ml-1 h-4 w-4 rounded flex items-center justify-center text-slate-400 hover:text-red-500 hover:bg-red-50 transition-all"
                                                >
                                                    <Trash2 className="h-2.5 w-2.5" />
                                                </button>
                                            </div>
                                        </div>
                                        <p className="text-[11px] text-slate-400 truncate mt-0.5 leading-tight">
                                            {thread.preview}
                                        </p>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>
            )}

            {/* Spacer when not on chat (to push bottom section down) */}
            {!isOnChat && <div className="flex-1" />}

            {/* ── Bottom: Settings + Sign Out + User ────────────────────── */}
            <div className={cn("shrink-0 border-t border-slate-200/80 py-2 space-y-0.5", collapsed ? "px-2" : "px-3")}>

                {/* Settings */}
                {collapsed ? (
                    <Tip label="Settings">
                        <Link href="/settings" className={cn(
                            "flex items-center justify-center h-9 w-full rounded-xl transition-colors text-slate-500 hover:bg-slate-100 hover:text-slate-800",
                            pathname.startsWith("/settings") && "bg-slate-100 text-slate-800"
                        )}>
                            <Settings className="h-[17px] w-[17px]" />
                        </Link>
                    </Tip>
                ) : (
                    <Link href="/settings" className={cn(
                        "flex items-center gap-3 rounded-xl px-3.5 py-2 text-[13px] font-medium transition-colors text-slate-500 hover:bg-slate-100 hover:text-slate-800",
                        pathname.startsWith("/settings") && "bg-slate-100 text-slate-800"
                    )}>
                        <Settings className="h-[17px] w-[17px] shrink-0" />
                        <span>Settings</span>
                    </Link>
                )}

                {/* Sign Out */}
                {user && (
                    collapsed ? (
                        <Tip label="Sign Out">
                            <button onClick={handleSignOut}
                                className="flex items-center justify-center h-9 w-full rounded-xl transition-colors text-slate-500 hover:bg-red-50 hover:text-red-500">
                                <LogOut className="h-[17px] w-[17px]" />
                            </button>
                        </Tip>
                    ) : (
                        <button onClick={handleSignOut}
                            className="w-full flex items-center gap-3 rounded-xl px-3.5 py-2 text-[13px] font-medium transition-colors text-slate-500 hover:bg-red-50 hover:text-red-500 text-left">
                            <LogOut className="h-[17px] w-[17px] shrink-0" />
                            <span>Sign Out</span>
                        </button>
                    )
                )}

                {/* User chip */}
                <div className={cn("pt-1 flex items-center gap-2.5", collapsed ? "justify-center" : "px-1")}>
                    {loading ? (
                        <div className="h-7 w-7 rounded-lg bg-slate-200 animate-pulse" />
                    ) : user ? (
                        collapsed ? (
                            <Tip label={`${user.full_name}`}>
                                <Avatar className="h-7 w-7 rounded-lg cursor-default">
                                    <AvatarFallback className="rounded-lg bg-orange-100 text-orange-700 font-bold text-[10px]">
                                        {getInitials(user.full_name)}
                                    </AvatarFallback>
                                </Avatar>
                            </Tip>
                        ) : (
                            <>
                                <Avatar className="h-7 w-7 rounded-lg shrink-0">
                                    <AvatarFallback className="rounded-lg bg-orange-100 text-orange-700 font-bold text-[10px]">
                                        {getInitials(user.full_name)}
                                    </AvatarFallback>
                                </Avatar>
                                <div className="overflow-hidden">
                                    <p className="text-[12px] font-semibold text-slate-700 truncate leading-tight">{user.full_name}</p>
                                    <p className="text-[10px] text-slate-400 capitalize">{user.role}</p>
                                </div>
                            </>
                        )
                    ) : null}
                </div>
            </div>
        </aside>
    );
}
