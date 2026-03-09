"use client";

import { useEffect, useState } from "react";
import {
    CreditCard, Edit2, Check, X, Plus, Zap, FileText, MessageSquare,
    RefreshCw, ToggleLeft, ToggleRight,
} from "lucide-react";
import {
    fetchPlans, fetchCreditRules, updateCreditRule, createCreditRule,
    Plan, CreditRule, fmtPaise,
} from "@/lib/admin-api";

// ── Plan Card ─────────────────────────────────────────────────────────────────
function PlanCard({ plan }: { plan: Plan }) {
    const COLORS: Record<string, string> = {
        starter: "#64748b",
        pro: "#6366f1",
        enterprise: "#f59e0b",
    };
    const color = COLORS[plan.id] || "#6366f1";

    return (
        <div style={{
            background: "#16181f", border: `1px solid ${color}44`,
            borderRadius: 14, padding: 24, position: "relative", overflow: "hidden",
        }}>
            {/* Glow bar */}
            <div style={{
                position: "absolute", top: 0, left: 0, right: 0, height: 3,
                background: `linear-gradient(90deg, ${color}, ${color}88)`,
            }} />

            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", color, textTransform: "uppercase", marginBottom: 8 }}>
                {plan.display_name}
            </div>

            <div style={{ fontSize: 28, fontWeight: 700, color: "#f1f5f9", marginBottom: 4 }}>
                {fmtPaise(plan.price_monthly_paise)}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 16 }}>
                <Row label="Credits / cycle" value={plan.max_credits_per_cycle.toLocaleString()} color={color} />
                <Row label="Max companies" value={plan.max_companies.toString()} color={color} />
                <Row label="Enforcement" value={plan.enforcement_mode.replace(/_/g, " ")} color={color} />
            </div>

            {/* Features */}
            <div style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid #1e2130" }}>
                {Object.entries(plan.features_json || {}).map(([k, v]) => (
                    <div key={k} style={{
                        display: "flex", alignItems: "center", gap: 6,
                        fontSize: 12, color: v ? "#94a3b8" : "#3d4557",
                        marginBottom: 4,
                    }}>
                        <span style={{ color: v ? color : "#3d4557" }}>{v ? "✓" : "✗"}</span>
                        {k.replace(/_/g, " ")}
                    </div>
                ))}
            </div>
        </div>
    );
}

function Row({ label, value, color }: { label: string; value: string; color: string }) {
    return (
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
            <span style={{ color: "#64748b" }}>{label}</span>
            <span style={{ color, fontWeight: 600 }}>{value}</span>
        </div>
    );
}

// ── Credit Rule Row ────────────────────────────────────────────────────────────
const TYPE_ICONS: Record<string, React.ReactNode> = {
    VOUCHER: <Zap size={13} color="#a5b4fc" />,
    DOCUMENT: <FileText size={13} color="#7dd3fc" />,
    MESSAGE: <MessageSquare size={13} color="#6ee7b7" />,
};

function CreditRuleRow({
    rule, onSave,
}: {
    rule: CreditRule;
    onSave: (id: string, data: { credits?: number; is_active?: boolean }) => Promise<void>;
}) {
    const [editing, setEditing] = useState(false);
    const [draft, setDraft] = useState(rule.credits.toString());
    const [saving, setSaving] = useState(false);

    const save = async () => {
        setSaving(true);
        try {
            await onSave(rule.id, { credits: parseFloat(draft) });
            setEditing(false);
        } catch (_) { }
        setSaving(false);
    };

    const toggleActive = async () => {
        setSaving(true);
        try { await onSave(rule.id, { is_active: !rule.is_active }); }
        catch (_) { }
        setSaving(false);
    };

    const TYPE_BG: Record<string, string> = {
        VOUCHER: "#6366f133", DOCUMENT: "#0ea5e933", MESSAGE: "#10b98133",
    };

    return (
        <div style={{
            display: "grid",
            gridTemplateColumns: "180px 180px 1fr 110px 80px",
            alignItems: "center", gap: 12,
            padding: "14px 20px",
            borderBottom: "1px solid #1e2130",
            opacity: rule.is_active ? 1 : 0.45,
        }}>
            {/* Type + icon */}
            <div style={{
                display: "inline-flex", alignItems: "center", gap: 6,
                padding: "4px 10px", borderRadius: 6,
                background: TYPE_BG[rule.event_type] || "#1e2130",
                fontSize: 12, fontWeight: 600,
                width: "fit-content",
            }}>
                {TYPE_ICONS[rule.event_type]}
                {rule.event_type}
            </div>

            {/* Subtype */}
            <code style={{
                fontSize: 12, color: "#94a3b8",
                background: "#1a1d27", padding: "3px 8px", borderRadius: 4,
            }}>
                {rule.event_subtype}
            </code>

            {/* Description */}
            <span style={{ fontSize: 12, color: "#64748b" }}>
                {rule.description || "—"}
            </span>

            {/* Credits — editable */}
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                {editing ? (
                    <>
                        <input
                            autoFocus
                            type="number" step="0.25" min="0" max="100"
                            value={draft}
                            onChange={e => setDraft(e.target.value)}
                            style={{
                                width: 60, padding: "4px 8px",
                                background: "#1a1d27", border: "1px solid #6366f1",
                                borderRadius: 6, color: "#e2e8f0", fontSize: 13,
                            }}
                        />
                        <button onClick={save} disabled={saving} style={{ background: "none", border: "none", cursor: "pointer", color: "#10b981" }}>
                            <Check size={14} />
                        </button>
                        <button onClick={() => { setEditing(false); setDraft(rule.credits.toString()); }} style={{ background: "none", border: "none", cursor: "pointer", color: "#64748b" }}>
                            <X size={14} />
                        </button>
                    </>
                ) : (
                    <>
                        <span style={{
                            fontSize: 15, fontWeight: 700,
                            color: rule.credits === 0 ? "#64748b" : "#a5b4fc",
                        }}>
                            {rule.credits} cr
                        </span>
                        <button onClick={() => setEditing(true)} style={{
                            background: "none", border: "none", cursor: "pointer",
                            color: "#64748b", padding: 2,
                        }}>
                            <Edit2 size={12} />
                        </button>
                    </>
                )}
            </div>

            {/* Toggle active */}
            <button onClick={toggleActive} disabled={saving} style={{
                background: "none", border: "none", cursor: "pointer",
                color: rule.is_active ? "#10b981" : "#64748b",
                display: "flex", alignItems: "center", gap: 4, fontSize: 12,
            }}>
                {rule.is_active
                    ? <><ToggleRight size={18} /> Active</>
                    : <><ToggleLeft size={18} /> Off</>}
            </button>
        </div>
    );
}

// ── New Rule Form ─────────────────────────────────────────────────────────────
function NewRuleForm({ onCreated }: { onCreated: () => void }) {
    const [open, setOpen] = useState(false);
    const [type, setType] = useState("VOUCHER");
    const [subtype, setSubtype] = useState("created");
    const [credits, setCredits] = useState("1");
    const [desc, setDesc] = useState("");
    const [saving, setSaving] = useState(false);
    const [msg, setMsg] = useState<string | null>(null);

    const SUBTYPES: Record<string, string[]> = {
        VOUCHER: ["created", "updated"],
        DOCUMENT: ["page_processed"],
        MESSAGE: ["action", "info_query"],
    };

    const save = async () => {
        setSaving(true);
        try {
            await createCreditRule({
                event_type: type,
                event_subtype: subtype,
                credits: parseFloat(credits),
                description: desc || undefined,
            });
            setMsg("✓ Rule created. Cache invalidated.");
            setTimeout(() => { setMsg(null); setOpen(false); }, 2000);
            onCreated();
        } catch (e: any) { setMsg(`Error: ${e.message}`); }
        setSaving(false);
    };

    if (!open) return (
        <button onClick={() => setOpen(true)} style={{
            display: "inline-flex", alignItems: "center", gap: 6,
            padding: "8px 14px", borderRadius: 8,
            background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
            border: "none", color: "#fff", fontWeight: 600, fontSize: 13, cursor: "pointer",
        }}>
            <Plus size={14} /> New Rule
        </button>
    );

    return (
        <div style={{
            background: "#16181f", border: "1px solid #6366f1",
            borderRadius: 12, padding: 20, marginBottom: 20,
        }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: "#a5b4fc", marginBottom: 14 }}>
                New Credit Rule
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 100px 1fr", gap: 10 }}>
                <div>
                    <label style={{ fontSize: 11, color: "#64748b", display: "block", marginBottom: 4 }}>Event Type</label>
                    <select value={type} onChange={e => { setType(e.target.value); setSubtype(SUBTYPES[e.target.value][0]); }}
                        style={{ width: "100%", padding: "8px 10px", background: "#1a1d27", border: "1px solid #2d3140", borderRadius: 6, color: "#e2e8f0", fontSize: 13 }}>
                        <option>VOUCHER</option><option>DOCUMENT</option><option>MESSAGE</option>
                    </select>
                </div>
                <div>
                    <label style={{ fontSize: 11, color: "#64748b", display: "block", marginBottom: 4 }}>Subtype</label>
                    <select value={subtype} onChange={e => setSubtype(e.target.value)}
                        style={{ width: "100%", padding: "8px 10px", background: "#1a1d27", border: "1px solid #2d3140", borderRadius: 6, color: "#e2e8f0", fontSize: 13 }}>
                        {(SUBTYPES[type] || []).map(s => <option key={s}>{s}</option>)}
                    </select>
                </div>
                <div>
                    <label style={{ fontSize: 11, color: "#64748b", display: "block", marginBottom: 4 }}>Credits</label>
                    <input type="number" step="0.25" min="0" value={credits} onChange={e => setCredits(e.target.value)}
                        style={{ width: "100%", padding: "8px 10px", background: "#1a1d27", border: "1px solid #2d3140", borderRadius: 6, color: "#e2e8f0", fontSize: 13, boxSizing: "border-box" }} />
                </div>
                <div>
                    <label style={{ fontSize: 11, color: "#64748b", display: "block", marginBottom: 4 }}>Description</label>
                    <input value={desc} onChange={e => setDesc(e.target.value)} placeholder="Optional..."
                        style={{ width: "100%", padding: "8px 10px", background: "#1a1d27", border: "1px solid #2d3140", borderRadius: 6, color: "#e2e8f0", fontSize: 13, boxSizing: "border-box" }} />
                </div>
            </div>
            <div style={{ display: "flex", gap: 10, marginTop: 12 }}>
                <button onClick={save} disabled={saving} style={{
                    padding: "8px 18px", borderRadius: 7,
                    background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                    border: "none", color: "#fff", fontWeight: 600, fontSize: 13, cursor: "pointer",
                }}>{saving ? "Saving..." : "Create Rule"}</button>
                <button onClick={() => setOpen(false)} style={{
                    padding: "8px 14px", borderRadius: 7, background: "#1a1d27",
                    border: "1px solid #2d3140", color: "#94a3b8", fontSize: 13, cursor: "pointer",
                }}>Cancel</button>
            </div>
            {msg && <div style={{ marginTop: 10, fontSize: 12, color: msg.startsWith("✓") ? "#10b981" : "#ef4444" }}>{msg}</div>}
        </div>
    );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function PlansPage() {
    const [plans, setPlans] = useState<Plan[]>([]);
    const [rules, setRules] = useState<CreditRule[]>([]);
    const [loading, setLoad] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = async () => {
        setLoad(true); setError(null);
        try {
            const [p, r] = await Promise.all([fetchPlans(), fetchCreditRules()]);
            setPlans(p.plans);
            setRules(r.credit_rules);
        } catch (e: any) { setError(e.message); }
        setLoad(false);
    };

    useEffect(() => { load(); }, []);

    const handleRuleSave = async (
        id: string,
        data: { credits?: number; is_active?: boolean }
    ) => {
        await updateCreditRule(id, data);
        // Optimistic update
        setRules(prev => prev.map(r => r.id === id ? { ...r, ...data } : r));
    };

    return (
        <div>
            {/* Header */}
            <div style={{ marginBottom: 32 }}>
                <h1 style={{ fontSize: 26, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Plans & Credit Rules</h1>
                <p style={{ color: "#64748b", fontSize: 14, marginTop: 4 }}>
                    Manage pricing tiers and configure how many credits each event consumes.
                </p>
            </div>

            {error && (
                <div style={{ padding: "12px 16px", borderRadius: 8, background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", color: "#fca5a5", fontSize: 13, marginBottom: 20 }}>
                    ⚠ {error}
                </div>
            )}

            {/* Plans grid */}
            <div style={{ marginBottom: 40 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                    <h2 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", margin: 0 }}>
                        <CreditCard size={16} style={{ display: "inline", marginRight: 8, color: "#a5b4fc" }} />
                        Pricing Plans
                    </h2>
                    <button onClick={load} style={{
                        display: "flex", alignItems: "center", gap: 6, padding: "7px 12px",
                        borderRadius: 7, background: "#1e2130", border: "1px solid #2d3140",
                        color: "#94a3b8", cursor: "pointer", fontSize: 12,
                    }}>
                        <RefreshCw size={12} className={loading ? "animate-spin" : ""} /> Refresh
                    </button>
                </div>

                {loading ? (
                    <div style={{ color: "#64748b", padding: 20 }}>Loading...</div>
                ) : (
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
                        {plans.map(p => <PlanCard key={p.id} plan={p} />)}
                    </div>
                )}
            </div>

            {/* Credit Rules */}
            <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                    <div>
                        <h2 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", margin: 0 }}>
                            Credit Rules
                        </h2>
                        <p style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
                            Changes take effect within ~5 minutes (in-process cache TTL).
                            Only active rules with effective dates covering today are applied.
                        </p>
                    </div>
                    <NewRuleForm onCreated={load} />
                </div>

                <div style={{
                    background: "#16181f", border: "1px solid #1e2130",
                    borderRadius: 12, overflow: "hidden",
                }}>
                    {/* Header */}
                    <div style={{
                        display: "grid",
                        gridTemplateColumns: "180px 180px 1fr 110px 80px",
                        padding: "10px 20px", gap: 12,
                        borderBottom: "1px solid #1e2130",
                        fontSize: 11, fontWeight: 600, letterSpacing: "0.05em",
                        color: "#64748b", textTransform: "uppercase",
                    }}>
                        <span>Event Type</span>
                        <span>Subtype</span>
                        <span>Description</span>
                        <span>Credits</span>
                        <span>Status</span>
                    </div>

                    {loading ? (
                        <div style={{ padding: "40px 20px", textAlign: "center", color: "#64748b" }}>Loading rules...</div>
                    ) : rules.length === 0 ? (
                        <div style={{ padding: "40px 20px", textAlign: "center", color: "#64748b" }}>
                            No credit rules found. Create one above.
                        </div>
                    ) : rules.map(r => (
                        <CreditRuleRow key={r.id} rule={r} onSave={handleRuleSave} />
                    ))}
                </div>

                <div style={{ marginTop: 12, fontSize: 12, color: "#64748b" }}>
                    {rules.length} rules · Cache TTL: 5 minutes ·
                    <span style={{ color: "#a5b4fc" }}> Inactive rules are dimmed and not applied.</span>
                </div>
            </div>
        </div>
    );
}
