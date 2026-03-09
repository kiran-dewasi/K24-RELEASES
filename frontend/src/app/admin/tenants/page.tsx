"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Search, Filter, Users, ArrowRight, RefreshCw } from "lucide-react";
import {
    fetchTenants, fetchPlans,
    TenantRow, Plan,
    fmtDate, fmtPaise, statusColor, creditStatusColor,
} from "@/lib/admin-api";

// ── Inline components to keep file self-contained ────────────────────────────

function CreditBar({ used, max, pct }: { used: number; max: number; pct: number }) {
    const color = creditStatusColor(pct);
    return (
        <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: 12 }}>
                <span style={{ color: "#94a3b8" }}>{used.toFixed(0)} / {max} cr</span>
                <span style={{ color, fontWeight: 600 }}>{pct.toFixed(0)}%</span>
            </div>
            <div style={{ height: 6, borderRadius: 99, background: "#1e2130", overflow: "hidden" }}>
                <div style={{
                    height: "100%", width: `${Math.min(pct, 100)}%`,
                    background: color,
                    borderRadius: 99,
                    transition: "width 0.4s ease",
                }} />
            </div>
        </div>
    );
}

function Badge({ label, color }: { label: string; color: string }) {
    return (
        <span style={{
            padding: "2px 8px", borderRadius: 99, fontSize: 11, fontWeight: 600,
            background: `${color}22`, color,
        }}>{label}</span>
    );
}

const PLAN_COLORS: Record<string, string> = {
    starter: "#64748b",
    pro: "#6366f1",
    enterprise: "#f59e0b",
};

// ── Page ─────────────────────────────────────────────────────────────────────

export default function TenantsPage() {
    const [tenants, setTenants] = useState<TenantRow[]>([]);
    const [plans, setPlans] = useState<Plan[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [filterPlan, setFilterPlan] = useState("");
    const [error, setError] = useState<string | null>(null);

    const load = async () => {
        setLoading(true);
        setError(null);
        try {
            const [td, pd] = await Promise.all([
                fetchTenants({ search: search || undefined, plan_id: filterPlan || undefined }),
                fetchPlans(),
            ]);
            setTenants(td.tenants);
            setPlans(pd.plans);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { load(); }, [search, filterPlan]);

    const totalCreditsUsed = tenants.reduce((s, t) => s + t.credits_used, 0);
    const totalTenants = tenants.length;
    const overLimit = tenants.filter(t => t.percent_used >= 100).length;
    const nearLimit = tenants.filter(t => t.percent_used >= 80 && t.percent_used < 100).length;

    return (
        <div>
            {/* Header */}
            <div style={{ marginBottom: 32 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div>
                        <h1 style={{ fontSize: 26, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Tenants</h1>
                        <p style={{ color: "#64748b", fontSize: 14, marginTop: 4 }}>
                            Usage and plan status for all K24 customers
                        </p>
                    </div>
                    <button onClick={load} style={{
                        display: "flex", alignItems: "center", gap: 6,
                        padding: "8px 14px", borderRadius: 8,
                        background: "#1e2130", border: "1px solid #2d3140",
                        color: "#94a3b8", cursor: "pointer", fontSize: 13,
                    }}>
                        <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> Refresh
                    </button>
                </div>
            </div>

            {/* Summary cards */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 28 }}>
                {[
                    { label: "Total Tenants", value: totalTenants, color: "#6366f1" },
                    { label: "Credits Consumed", value: totalCreditsUsed.toFixed(0), color: "#10b981" },
                    { label: "Near Limit (≥80%)", value: nearLimit, color: "#f59e0b" },
                    { label: "Over Limit", value: overLimit, color: "#ef4444" },
                ].map(({ label, value, color }) => (
                    <div key={label} style={{
                        background: "#16181f", border: "1px solid #1e2130",
                        borderRadius: 12, padding: "20px 24px",
                    }}>
                        <div style={{ fontSize: 12, color: "#64748b", marginBottom: 8 }}>{label}</div>
                        <div style={{ fontSize: 30, fontWeight: 700, color }}>{value}</div>
                    </div>
                ))}
            </div>

            {/* Filters */}
            <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
                <div style={{ position: "relative", flex: 1 }}>
                    <Search size={15} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#64748b" }} />
                    <input
                        placeholder="Search by company name..."
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        style={{
                            width: "100%", padding: "9px 12px 9px 36px",
                            background: "#16181f", border: "1px solid #1e2130",
                            borderRadius: 8, color: "#e2e8f0", fontSize: 13,
                            outline: "none", boxSizing: "border-box",
                        }}
                    />
                </div>
                <select
                    value={filterPlan}
                    onChange={e => setFilterPlan(e.target.value)}
                    style={{
                        padding: "9px 14px", background: "#16181f",
                        border: "1px solid #1e2130", borderRadius: 8,
                        color: "#e2e8f0", fontSize: 13, cursor: "pointer",
                    }}
                >
                    <option value="">All Plans</option>
                    {plans.map(p => (
                        <option key={p.id} value={p.id}>{p.display_name}</option>
                    ))}
                </select>
            </div>

            {/* Error */}
            {error && (
                <div style={{
                    padding: "12px 16px", borderRadius: 8,
                    background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
                    color: "#fca5a5", fontSize: 13, marginBottom: 16,
                }}>⚠ {error}</div>
            )}

            {/* Table */}
            <div style={{
                background: "#16181f", border: "1px solid #1e2130",
                borderRadius: 12, overflow: "hidden",
            }}>
                {/* Table header */}
                <div style={{
                    display: "grid",
                    gridTemplateColumns: "2fr 1fr 1fr 1fr 2fr 1fr 40px",
                    padding: "12px 20px",
                    borderBottom: "1px solid #1e2130",
                    fontSize: 11, fontWeight: 600, letterSpacing: "0.05em",
                    color: "#64748b", textTransform: "uppercase",
                }}>
                    <span>Tenant</span><span>Plan</span><span>Status</span>
                    <span>Companies</span><span>Credits Used</span><span>Cycle End</span><span />
                </div>

                {/* Rows */}
                {loading ? (
                    <div style={{ padding: "48px 20px", textAlign: "center", color: "#64748b" }}>Loading...</div>
                ) : tenants.length === 0 ? (
                    <div style={{ padding: "48px 20px", textAlign: "center", color: "#64748b" }}>
                        No tenants found.
                    </div>
                ) : tenants.map((t, i) => (
                    <div key={t.tenant_id} style={{
                        display: "grid",
                        gridTemplateColumns: "2fr 1fr 1fr 1fr 2fr 1fr 40px",
                        padding: "16px 20px", alignItems: "center",
                        borderBottom: i < tenants.length - 1 ? "1px solid #1e2130" : "none",
                        transition: "background 0.1s",
                    }}
                        onMouseEnter={e => (e.currentTarget.style.background = "#1a1d27")}
                        onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                    >
                        {/* Company */}
                        <div>
                            <div style={{ fontWeight: 600, fontSize: 14, color: "#f1f5f9" }}>
                                {t.company_name || "—"}
                            </div>
                            <div style={{ fontSize: 11, color: "#64748b", marginTop: 2, fontFamily: "monospace" }}>
                                {t.tenant_id}
                            </div>
                        </div>

                        {/* Plan */}
                        <Badge label={t.plan_name} color={PLAN_COLORS[t.plan_id] || "#6366f1"} />

                        {/* Status */}
                        <span style={{ fontSize: 13 }} className={statusColor(t.plan_status)}>
                            {t.plan_status}
                        </span>

                        {/* Companies */}
                        <span style={{ fontSize: 13, color: "#94a3b8" }}>{t.companies_count}</span>

                        {/* Credit bar */}
                        <div style={{ paddingRight: 16 }}>
                            <CreditBar used={t.credits_used} max={t.max_credits} pct={t.percent_used} />
                        </div>

                        {/* Cycle end */}
                        <span style={{ fontSize: 12, color: "#64748b" }}>{fmtDate(t.next_cycle_end)}</span>

                        {/* Arrow */}
                        <Link href={`/admin/tenants/${t.tenant_id}`} style={{ color: "#6366f1" }}>
                            <ArrowRight size={16} />
                        </Link>
                    </div>
                ))}
            </div>

            <div style={{ marginTop: 12, fontSize: 12, color: "#64748b" }}>
                {tenants.length} tenant{tenants.length !== 1 ? "s" : ""} shown
            </div>
        </div>
    );
}
