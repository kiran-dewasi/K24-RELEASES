"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    LayoutDashboard, Users, CreditCard, BookOpen, BarChart3, Shield, Receipt
} from "lucide-react";

const NAV = [
    { href: "/admin/tenants", label: "Tenants", icon: Users },
    { href: "/admin/plans", label: "Plans & Rules", icon: CreditCard },
    { href: "/admin/subscriptions", label: "Subscriptions", icon: Receipt },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();

    return (
        <div className="min-h-screen flex" style={{ background: "var(--bg-base, #0f1117)", color: "#e2e8f0", fontFamily: "Inter, system-ui, sans-serif" }}>

            {/* Sidebar */}
            <aside style={{
                width: 220, flexShrink: 0,
                background: "#16181f",
                borderRight: "1px solid #1e2130",
                display: "flex", flexDirection: "column",
                padding: "24px 0",
            }}>
                {/* Logo */}
                <div style={{ padding: "0 24px 28px", borderBottom: "1px solid #1e2130" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <div style={{
                            width: 32, height: 32, borderRadius: 8,
                            background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                            display: "flex", alignItems: "center", justifyContent: "center",
                            fontWeight: 700, fontSize: 14, color: "#fff"
                        }}>K</div>
                        <div>
                            <div style={{ fontWeight: 700, fontSize: 15, color: "#f1f5f9" }}>K24 Admin</div>
                            <div style={{ fontSize: 11, color: "#64748b" }}>Internal Portal</div>
                        </div>
                    </div>
                </div>

                {/* Nav */}
                <nav style={{ flex: 1, padding: "16px 12px", display: "flex", flexDirection: "column", gap: 4 }}>
                    {NAV.map(({ href, label, icon: Icon }) => {
                        const active = pathname.startsWith(href);
                        return (
                            <Link key={href} href={href} style={{
                                display: "flex", alignItems: "center", gap: 10,
                                padding: "9px 12px", borderRadius: 8, textDecoration: "none",
                                fontSize: 14, fontWeight: active ? 600 : 400,
                                color: active ? "#a5b4fc" : "#94a3b8",
                                background: active ? "rgba(99,102,241,0.12)" : "transparent",
                                transition: "all 0.15s",
                            }}>
                                <Icon size={16} />
                                {label}
                            </Link>
                        );
                    })}
                </nav>

                {/* Footer badge */}
                <div style={{ padding: "16px 24px", borderTop: "1px solid #1e2130" }}>
                    <div style={{
                        display: "inline-flex", alignItems: "center", gap: 6,
                        padding: "4px 10px", borderRadius: 6,
                        background: "rgba(16,185,129,0.1)", color: "#10b981",
                        fontSize: 11, fontWeight: 600,
                    }}>
                        <Shield size={10} /> Internal Only
                    </div>
                </div>
            </aside>

            {/* Main */}
            <main style={{ flex: 1, overflowY: "auto", padding: "32px 40px" }}>
                {children}
            </main>
        </div>
    );
}
