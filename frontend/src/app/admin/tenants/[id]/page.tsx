"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
    ArrowLeft, FileText, MessageSquare, Zap, Brain, TrendingUp,
    CheckCircle, AlertTriangle, XCircle, Clock,
} from "lucide-react";
import {
    fetchTenantDetail, assignPlan, fetchPlans,
    TenantDetail, Plan, UsageEvent,
    fmtDate, creditStatusColor,
} from "@/lib/admin-api";

// ── Mini Components ───────────────────────────────────────────────────────────

function StatCard({
    label, value, sub, color = "#6366f1",
}: { label: string; value: string | number; sub?: string; color?: string }) {
    return (
        <div style={{
            background: "#16181f", border: "1px solid #1e2130",
            borderRadius: 12, padding: "20px 24px",
        }}>
            <div style={{ fontSize: 12, color: "#64748b", marginBottom: 8 }}>{label}</div>
            <div style={{ fontSize: 26, fontWeight: 700, color }}>{value}</div>
            {sub && <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>{sub}</div>}
        </div>
    );
}

function DonutChart({ pct, size = 120 }: { pct: number; size?: number }) {
    const r = size / 2 - 10;
    const circ = 2 * Math.PI * r;
    const dash = (Math.min(pct, 100) / 100) * circ;
    const color = creditStatusColor(pct);
    return (
        <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
            <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#1e2130" strokeWidth={12} />
            <circle
                cx={size / 2} cy={size / 2} r={r} fill="none"
                stroke={color} strokeWidth={12}
                strokeDasharray={`${dash} ${circ}`}
                strokeLinecap="round"
                style={{ transition: "stroke-dasharray 0.6s ease" }}
            />
            <text
                x={size / 2} y={size / 2}
                textAnchor="middle" dominantBaseline="central"
                fill={color} fontWeight="700" fontSize="18"
                style={{ transform: "rotate(90deg)", transformOrigin: `${size / 2}px ${size / 2}px` }}
            >
                {pct.toFixed(0)}%
            </text>
        </svg>
    );
}

const EVENT_ICONS: Record<string, React.ReactNode> = {
    VOUCHER: <Zap size={14} />,
    DOCUMENT: <FileText size={14} />,
    MESSAGE: <MessageSquare size={14} />,
};

const STATUS_ICONS: Record<string, React.ReactNode> = {
    ALLOWED: <CheckCircle size={12} color="#10b981" />,
    NEAR_LIMIT: <AlertTriangle size={12} color="#f59e0b" />,
    OVER_LIMIT: <AlertTriangle size={12} color="#ef4444" />,
    BLOCKED: <XCircle size={12} color="#ef4444" />,
};

function EventRow({ ev }: { ev: UsageEvent }) {
    const bg: Record<string, string> = {
        VOUCHER: "#6366f133", DOCUMENT: "#0ea5e933", MESSAGE: "#10b98133",
    };
    const fg: Record<string, string> = {
        VOUCHER: "#a5b4fc", DOCUMENT: "#7dd3fc", MESSAGE: "#6ee7b7",
    };
    return (
        <div style={{
            display: "flex", alignItems: "center", gap: 12,
            padding: "12px 0", borderBottom: "1px solid #1e2130",
        }}>
            <div style={{
                width: 32, height: 32, borderRadius: 8, flexShrink: 0,
                background: bg[ev.event_type] || "#1e2130",
                color: fg[ev.event_type] || "#94a3b8",
                display: "flex", alignItems: "center", justifyContent: "center",
            }}>
                {EVENT_ICONS[ev.event_type]}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, color: "#e2e8f0", fontWeight: 500 }}>
                    {ev.event_type} / {ev.event_subtype}
                </div>
                <div style={{ fontSize: 11, color: "#64748b", marginTop: 2 }}>
                    via {ev.source} · {new Date(ev.created_at).toLocaleString("en-IN")}
                </div>
            </div>
            <div style={{ textAlign: "right", flexShrink: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: ev.credits_consumed > 0 ? "#a5b4fc" : "#64748b" }}>
                    {ev.credits_consumed > 0 ? `-${ev.credits_consumed} cr` : "0 cr"}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 4, justifyContent: "flex-end", marginTop: 2 }}>
                    {STATUS_ICONS[ev.status]}
                    <span style={{ fontSize: 10, color: "#64748b" }}>{ev.status}</span>
                </div>
            </div>
        </div>
    );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function TenantDetailPage() {
    const { id } = useParams<{ id: string }>();
    const [detail, setDetail] = useState<TenantDetail | null>(null);
    const [plans, setPlans] = useState<Plan[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Plan assignment
    const [assigning, setAssigning] = useState(false);
    const [newPlan, setNewPlan] = useState("");
    const [assignNote, setAssignNote] = useState("");
    const [assignMsg, setAssignMsg] = useState<string | null>(null);

    useEffect(() => {
        (async () => {
            setLoading(true);
            try {
                const [d, p] = await Promise.all([fetchTenantDetail(id), fetchPlans()]);
                setDetail(d);
                setPlans(p.plans);
                setNewPlan(d.plan.plan_id);
            } catch (e: any) { setError(e.message); }
            finally { setLoading(false); }
        })();
    }, [id]);

    if (loading) return <div style={{ color: "#64748b", padding: 48 }}>Loading...</div>;
    if (error) return <div style={{ color: "#ef4444", padding: 48 }}>Error: {error}</div>;
    if (!detail) return null;

    const { tenant, plan, current_cycle: cy, recent_events, llm_summary: llm } = detail;

    const handleAssignPlan = async () => {
        if (!newPlan) return;
        setAssigning(true);
        try {
            await assignPlan(tenant.id, { plan_id: newPlan, status: "active", notes: assignNote || undefined });
            setAssignMsg(`✓ Assigned to ${newPlan}`);
            setTimeout(() => setAssignMsg(null), 3000);
            // Reload
            const d = await fetchTenantDetail(id);
            setDetail(d);
        } catch (e: any) { setAssignMsg(`Error: ${e.message}`); }
        setAssigning(false);
    };

    const barStyle = (pct: number, color: string) => ({
        height: 8, borderRadius: 99, background: "#1e2130", overflow: "hidden",
        marginTop: 6,
    });

    return (
        <div>
            {/* Back */}
            <Link href="/admin/tenants" style={{
                display: "inline-flex", alignItems: "center", gap: 6,
                color: "#64748b", textDecoration: "none", fontSize: 13, marginBottom: 24,
            }}>
                <ArrowLeft size={14} /> Tenants
            </Link>

            {/* Header */}
            <div style={{ marginBottom: 32 }}>
                <h1 style={{ fontSize: 26, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>
                    {tenant.company_name || tenant.id}
                </h1>
                <div style={{ color: "#64748b", fontSize: 13, marginTop: 4 }}>
                    {tenant.whatsapp_number && <span>📱 {tenant.whatsapp_number} · </span>}
                    <span style={{ fontFamily: "monospace" }}>{tenant.id}</span>
                    {tenant.created_at && <span> · Joined {fmtDate(tenant.created_at)}</span>}
                </div>
            </div>

            {/* Top grid */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 16, marginBottom: 28 }}>
                <StatCard label="Plan" value={plan.plan_name} color="#a5b4fc" />
                <StatCard label="Credits Used" value={cy.credits_used_total.toFixed(0)}
                    sub={`of ${cy.max_credits} max`} color={creditStatusColor(cy.percent_used)} />
                <StatCard label="Total Events" value={cy.events_count_total.toString()} color="#10b981" />
                <StatCard label="LLM Calls" value={llm.total_calls.toString()}
                    sub={`$${llm.total_cost_usd.toFixed(4)}`} color="#f59e0b" />
            </div>

            {/* Two-column: Usage breakdown + Assign Plan */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 24 }}>

                {/* Usage breakdown card */}
                <div style={{
                    background: "#16181f", border: "1px solid #1e2130",
                    borderRadius: 12, padding: 24,
                }}>
                    <h2 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", margin: "0 0 20px" }}>
                        Credit Breakdown — Current Cycle
                    </h2>

                    {/* Donut + bar breakdown */}
                    <div style={{ display: "flex", gap: 24, alignItems: "center" }}>
                        <DonutChart pct={cy.percent_used} size={110} />
                        <div style={{ flex: 1 }}>
                            {[
                                { label: "Vouchers", used: cy.credits_used_voucher, events: cy.events_count_voucher, color: "#a5b4fc" },
                                { label: "Documents", used: cy.credits_used_document, events: cy.events_count_document, color: "#7dd3fc" },
                                { label: "Messages", used: cy.credits_used_message, events: cy.events_count_message, color: "#6ee7b7" },
                            ].map(({ label, used, events, color }) => {
                                const pct = cy.max_credits > 0 ? (used / cy.max_credits) * 100 : 0;
                                return (
                                    <div key={label} style={{ marginBottom: 14 }}>
                                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                                            <span style={{ color: "#94a3b8" }}>{label}</span>
                                            <span style={{ color }}>{used.toFixed(0)} cr · {events} events</span>
                                        </div>
                                        <div style={barStyle(pct, color)}>
                                            <div style={{ height: "100%", width: `${Math.min(pct, 100)}%`, background: color, borderRadius: 99 }} />
                                        </div>
                                    </div>
                                );
                            })}
                            <div style={{ marginTop: 16, fontSize: 12, color: "#64748b" }}>
                                Cycle: {fmtDate(cy.cycle_start)} → {fmtDate(cy.cycle_end)}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Assign Plan card */}
                <div style={{
                    background: "#16181f", border: "1px solid #1e2130",
                    borderRadius: 12, padding: 24,
                }}>
                    <h2 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", margin: "0 0 8px" }}>
                        Plan Management
                    </h2>
                    <p style={{ fontSize: 13, color: "#64748b", marginBottom: 20 }}>
                        Current: <span style={{ color: "#a5b4fc", fontWeight: 600 }}>{plan.plan_name}</span> ·
                        Status: <span style={{ fontWeight: 600 }}>{plan.status}</span> ·
                        Mode: {plan.enforcement_mode}
                    </p>

                    <div style={{ marginBottom: 12 }}>
                        <label style={{ display: "block", fontSize: 12, color: "#94a3b8", marginBottom: 6 }}>
                            Assign New Plan
                        </label>
                        <select
                            value={newPlan} onChange={e => setNewPlan(e.target.value)}
                            style={{
                                width: "100%", padding: "9px 12px",
                                background: "#1a1d27", border: "1px solid #2d3140",
                                borderRadius: 8, color: "#e2e8f0", fontSize: 13,
                            }}
                        >
                            {plans.map(p => (
                                <option key={p.id} value={p.id}>
                                    {p.display_name} — {p.max_credits_per_cycle} credits
                                </option>
                            ))}
                        </select>
                    </div>

                    <div style={{ marginBottom: 16 }}>
                        <label style={{ display: "block", fontSize: 12, color: "#94a3b8", marginBottom: 6 }}>
                            Notes (optional)
                        </label>
                        <input
                            value={assignNote} onChange={e => setAssignNote(e.target.value)}
                            placeholder="e.g. Enterprise custom terms..."
                            style={{
                                width: "100%", padding: "9px 12px",
                                background: "#1a1d27", border: "1px solid #2d3140",
                                borderRadius: 8, color: "#e2e8f0", fontSize: 13,
                                boxSizing: "border-box",
                            }}
                        />
                    </div>

                    <button
                        onClick={handleAssignPlan}
                        disabled={assigning}
                        style={{
                            width: "100%", padding: "10px",
                            background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                            border: "none", borderRadius: 8, color: "#fff",
                            fontWeight: 600, fontSize: 14, cursor: assigning ? "not-allowed" : "pointer",
                            opacity: assigning ? 0.7 : 1,
                        }}
                    >
                        {assigning ? "Assigning..." : "Assign Plan"}
                    </button>

                    {assignMsg && (
                        <div style={{
                            marginTop: 10, padding: "8px 12px", borderRadius: 6,
                            background: assignMsg.startsWith("✓") ? "rgba(16,185,129,0.1)" : "rgba(239,68,68,0.1)",
                            color: assignMsg.startsWith("✓") ? "#10b981" : "#f87171",
                            fontSize: 12,
                        }}>{assignMsg}</div>
                    )}

                    <div style={{ marginTop: 16, padding: 12, borderRadius: 8, background: "#1a1d27" }}>
                        <div style={{ fontSize: 12, color: "#64748b", marginBottom: 6 }}>Plan Features</div>
                        {Object.entries(plan.features).map(([k, v]) => (
                            <div key={k} style={{ display: "flex", gap: 8, fontSize: 12, color: v ? "#10b981" : "#64748b", marginBottom: 2 }}>
                                <span>{v ? "✓" : "✗"}</span> {k.replace(/_/g, " ")}
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Bottom: Events + LLM */}
            <div style={{ display: "grid", gridTemplateColumns: "3fr 2fr", gap: 20 }}>

                {/* Recent events */}
                <div style={{
                    background: "#16181f", border: "1px solid #1e2130",
                    borderRadius: 12, padding: 24,
                }}>
                    <h2 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", margin: "0 0 16px" }}>
                        Recent Events
                    </h2>
                    {recent_events.length === 0 ? (
                        <div style={{ color: "#64748b", fontSize: 13 }}>No events yet this cycle.</div>
                    ) : recent_events.map(ev => <EventRow key={ev.id} ev={ev} />)}
                </div>

                {/* LLM summary */}
                <div style={{
                    background: "#16181f", border: "1px solid #1e2130",
                    borderRadius: 12, padding: 24,
                }}>
                    <h2 style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 16, fontWeight: 600, color: "#f1f5f9", margin: "0 0 16px" }}>
                        <Brain size={16} color="#f59e0b" /> LLM Costs
                    </h2>

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 20 }}>
                        <div style={{ background: "#1a1d27", borderRadius: 8, padding: 12 }}>
                            <div style={{ fontSize: 11, color: "#64748b" }}>Total Calls</div>
                            <div style={{ fontSize: 20, fontWeight: 700, color: "#f59e0b", marginTop: 4 }}>{llm.total_calls}</div>
                        </div>
                        <div style={{ background: "#1a1d27", borderRadius: 8, padding: 12 }}>
                            <div style={{ fontSize: 11, color: "#64748b" }}>Est. Cost (USD)</div>
                            <div style={{ fontSize: 20, fontWeight: 700, color: "#ef4444", marginTop: 4 }}>${llm.total_cost_usd.toFixed(4)}</div>
                        </div>
                        <div style={{ background: "#1a1d27", borderRadius: 8, padding: 12 }}>
                            <div style={{ fontSize: 11, color: "#64748b" }}>Input Tokens</div>
                            <div style={{ fontSize: 18, fontWeight: 700, color: "#94a3b8", marginTop: 4 }}>
                                {(llm.total_tokens_in / 1000).toFixed(1)}k
                            </div>
                        </div>
                        <div style={{ background: "#1a1d27", borderRadius: 8, padding: 12 }}>
                            <div style={{ fontSize: 11, color: "#64748b" }}>Output Tokens</div>
                            <div style={{ fontSize: 18, fontWeight: 700, color: "#94a3b8", marginTop: 4 }}>
                                {(llm.total_tokens_out / 1000).toFixed(1)}k
                            </div>
                        </div>
                    </div>

                    <div style={{ fontSize: 12, color: "#64748b", marginBottom: 8, fontWeight: 600 }}>Top Workflows</div>
                    {llm.top_workflows.slice(0, 5).map(wf => (
                        <div key={wf.workflow} style={{
                            display: "flex", justifyContent: "space-between",
                            padding: "7px 0", borderBottom: "1px solid #1e2130", fontSize: 12,
                        }}>
                            <span style={{ color: "#94a3b8" }}>{wf.workflow}</span>
                            <span style={{ color: "#f59e0b" }}>${wf.cost_usd.toFixed(4)}</span>
                        </div>
                    ))}
                    {llm.top_workflows.length === 0 && (
                        <div style={{ color: "#64748b", fontSize: 12 }}>No LLM calls logged yet.</div>
                    )}
                </div>
            </div>
        </div>
    );
}
