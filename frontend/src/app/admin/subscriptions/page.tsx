"use client";

import { useState, useEffect, useCallback } from "react";
import { Clock, CheckCircle, XCircle, AlertCircle, RefreshCw, ChevronDown, ChevronUp, Search } from "lucide-react";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8001";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "k24-secret-key-123";

interface Intent {
    id: string;
    plan_id: string;
    amount_paise: number;
    name: string;
    company_name: string;
    email: string;
    phone: string;
    gst_number: string | null;
    upi_ref: string | null;
    screenshot_url: string | null;
    status: string;
    admin_note: string | null;
    activated_tenant_id: string | null;
    activated_at: string | null;
    created_at: string;
    updated_at: string;
}

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ElementType }> = {
    pending_payment: { label: "Payment Pending", color: "text-orange-400 bg-orange-500/10 border-orange-500/20", icon: Clock },
    awaiting_verification: { label: "Awaiting Verification", color: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20", icon: AlertCircle },
    activated: { label: "Activated", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20", icon: CheckCircle },
    rejected: { label: "Rejected", color: "text-red-400 bg-red-500/10 border-red-500/20", icon: XCircle },
};

const PLAN_COLORS: Record<string, string> = {
    starter: "bg-slate-500/20 text-slate-300",
    pro: "bg-indigo-500/20 text-indigo-300",
    enterprise: "bg-violet-500/20 text-violet-300",
};

function formatINR(paise: number) {
    return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(paise / 100);
}

function timeAgo(iso: string) {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
}

// ─── Intent Row ──────────────────────────────────────────────────────────────

function IntentRow({ intent, onAction }: { intent: Intent; onAction: () => void }) {
    const [expanded, setExpanded] = useState(false);
    const [note, setNote] = useState("");
    const [loading, setLoading] = useState(false);
    const [actionDone, setActionDone] = useState(false);

    const cfg = STATUS_CONFIG[intent.status] || STATUS_CONFIG.pending_payment;
    const Icon = cfg.icon;

    const canAct = intent.status === "awaiting_verification" || intent.status === "pending_payment";

    const take = async (status: "activated" | "rejected") => {
        setLoading(true);
        try {
            const res = await fetch(`${BACKEND_URL}/admin/subscription-intents/${intent.id}/status`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
                body: JSON.stringify({ status, admin_note: note || undefined }),
            });
            if (res.ok) {
                setActionDone(true);
                onAction();
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={`rounded-2xl border ${expanded ? "border-white/10" : "border-white/5"} bg-slate-900/50 overflow-hidden transition-all`}>
            <div
                className="flex items-center gap-4 p-4 cursor-pointer hover:bg-white/2 transition-colors"
                onClick={() => setExpanded(!expanded)}
            >
                {/* Plan badge */}
                <span className={`px-2.5 py-0.5 rounded-lg text-xs font-semibold uppercase ${PLAN_COLORS[intent.plan_id] || "bg-slate-500/20 text-slate-300"}`}>
                    {intent.plan_id}
                </span>

                {/* User info */}
                <div className="flex-1 min-w-0">
                    <p className="text-white font-medium text-sm truncate">{intent.name}</p>
                    <p className="text-slate-500 text-xs truncate">{intent.company_name} · {intent.email}</p>
                </div>

                {/* Amount */}
                <span className="text-white font-bold text-sm shrink-0">{formatINR(intent.amount_paise)}</span>

                {/* Status */}
                <span className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-xl border text-xs font-medium ${cfg.color}`}>
                    <Icon className="h-3 w-3" />
                    {cfg.label}
                </span>

                {/* Time */}
                <span className="text-slate-500 text-xs shrink-0 hidden md:block">{timeAgo(intent.created_at)}</span>

                {expanded ? <ChevronUp className="h-4 w-4 text-slate-400 shrink-0" /> : <ChevronDown className="h-4 w-4 text-slate-400 shrink-0" />}
            </div>

            {expanded && (
                <div className="border-t border-white/5 p-4 space-y-4">
                    {/* Details grid */}
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                        {[
                            { label: "Phone", value: intent.phone },
                            { label: "GST", value: intent.gst_number || "—" },
                            { label: "UPI Ref", value: intent.upi_ref || "Not submitted yet" },
                            { label: "Status", value: cfg.label },
                            { label: "Created", value: new Date(intent.created_at).toLocaleString("en-IN") },
                            { label: "Tenant ID", value: intent.activated_tenant_id || "—" },
                        ].map(({ label, value }) => (
                            <div key={label} className="bg-slate-800/50 rounded-xl p-2.5">
                                <p className="text-slate-500 mb-0.5">{label}</p>
                                <p className="text-white font-medium truncate">{value}</p>
                            </div>
                        ))}
                    </div>

                    {intent.screenshot_url && (
                        <a href={intent.screenshot_url} target="_blank" rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300">
                            📎 View Payment Screenshot
                        </a>
                    )}

                    {intent.admin_note && (
                        <div className="p-3 rounded-xl bg-amber-500/5 border border-amber-500/10 text-xs text-amber-300">
                            Note: {intent.admin_note}
                        </div>
                    )}

                    {/* Action buttons */}
                    {canAct && !actionDone && (
                        <div className="space-y-2.5 pt-1">
                            <textarea
                                value={note}
                                onChange={e => setNote(e.target.value)}
                                placeholder="Admin note (optional)..."
                                rows={2}
                                className="w-full bg-slate-800/60 border border-white/5 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/40 resize-none"
                            />
                            <div className="flex gap-3">
                                <button
                                    onClick={() => take("activated")}
                                    disabled={loading}
                                    className="flex-1 py-2.5 rounded-xl bg-emerald-600/20 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-600/30 text-sm font-medium transition-all disabled:opacity-50"
                                >
                                    {loading ? "Processing..." : "✓ Activate Subscription"}
                                </button>
                                <button
                                    onClick={() => take("rejected")}
                                    disabled={loading}
                                    className="flex-1 py-2.5 rounded-xl bg-red-600/10 border border-red-500/20 text-red-400 hover:bg-red-600/20 text-sm font-medium transition-all disabled:opacity-50"
                                >
                                    ✕ Reject
                                </button>
                            </div>
                        </div>
                    )}

                    {actionDone && (
                        <div className="flex items-center gap-2 text-emerald-400 text-sm">
                            <CheckCircle className="h-4 w-4" /> Action taken — refresh to see update.
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdminSubscriptionsPage() {
    const [intents, setIntents] = useState<Intent[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<string>("all");
    const [search, setSearch] = useState("");
    const [lastRefresh, setLastRefresh] = useState(new Date());

    const fetch_intents = useCallback(async (status?: string) => {
        setLoading(true);
        try {
            const url = status && status !== "all"
                ? `${BACKEND_URL}/admin/subscription-intents?status=${status}&limit=100`
                : `${BACKEND_URL}/admin/subscription-intents?limit=100`;
            const res = await fetch(url, { headers: { "X-API-Key": API_KEY } });
            const json = await res.json();
            setIntents(json.intents || []);
            setLastRefresh(new Date());
        } catch {
            setIntents([]);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetch_intents(filter); }, [filter, fetch_intents]);

    const filtered = intents.filter(i => {
        if (!search) return true;
        const s = search.toLowerCase();
        return (
            i.name.toLowerCase().includes(s) ||
            i.company_name.toLowerCase().includes(s) ||
            i.email.toLowerCase().includes(s) ||
            (i.upi_ref || "").includes(s)
        );
    });

    const counts = intents.reduce<Record<string, number>>((acc, i) => {
        acc[i.status] = (acc[i.status] || 0) + 1;
        return acc;
    }, {});

    const FILTER_TABS = [
        { id: "all", label: "All", count: intents.length },
        { id: "awaiting_verification", label: "Needs Action", count: counts["awaiting_verification"] || 0 },
        { id: "pending_payment", label: "Pending Payment", count: counts["pending_payment"] || 0 },
        { id: "activated", label: "Activated", count: counts["activated"] || 0 },
        { id: "rejected", label: "Rejected", count: counts["rejected"] || 0 },
    ];

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-3">
                <div>
                    <h1 className="text-xl font-bold text-white">Subscription Intents</h1>
                    <p className="text-slate-400 text-sm mt-0.5">UPI payment verification queue · Last updated {lastRefresh.toLocaleTimeString("en-IN")}</p>
                </div>
                <button
                    onClick={() => fetch_intents(filter)}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-white/10 text-slate-400 hover:text-white hover:bg-white/5 text-sm transition-all"
                >
                    <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
                </button>
            </div>

            {/* Summary cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                    { label: "Needs Action", count: counts["awaiting_verification"] || 0, color: "text-yellow-400" },
                    { label: "Activated", count: counts["activated"] || 0, color: "text-emerald-400" },
                    { label: "Pending Payment", count: counts["pending_payment"] || 0, color: "text-orange-400" },
                    { label: "Total", count: intents.length, color: "text-indigo-400" },
                ].map(({ label, count, color }) => (
                    <div key={label} className="p-4 rounded-2xl bg-slate-900/50 border border-white/5">
                        <p className={`text-2xl font-bold ${color}`}>{count}</p>
                        <p className="text-slate-500 text-xs mt-0.5">{label}</p>
                    </div>
                ))}
            </div>

            {/* Filters + Search */}
            <div className="flex flex-col sm:flex-row gap-3">
                <div className="flex gap-2 overflow-x-auto pb-1">
                    {FILTER_TABS.map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setFilter(tab.id)}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-all ${filter === tab.id
                                    ? "bg-indigo-600 text-white"
                                    : "bg-slate-800/60 text-slate-400 hover:text-white border border-white/5"
                                }`}
                        >
                            {tab.label}
                            {tab.count > 0 && (
                                <span className={`px-1.5 py-0.5 rounded-md text-[10px] ${filter === tab.id ? "bg-white/20" : "bg-white/5"}`}>
                                    {tab.count}
                                </span>
                            )}
                        </button>
                    ))}
                </div>
                <div className="relative flex-1 max-w-xs ml-auto">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" />
                    <input
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        placeholder="Search name, email, UTR..."
                        className="w-full bg-slate-800/60 border border-white/5 rounded-xl pl-8 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/30"
                    />
                </div>
            </div>

            {/* List */}
            <div className="space-y-2">
                {loading ? (
                    <div className="text-center py-16 text-slate-500">
                        <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-3 text-indigo-400" />
                        Loading...
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="text-center py-16 text-slate-500">
                        <CheckCircle className="h-6 w-6 mx-auto mb-3 text-slate-600" />
                        {search ? "No results for your search." : "No intents in this category."}
                    </div>
                ) : (
                    filtered.map(intent => (
                        <IntentRow key={intent.id} intent={intent} onAction={() => fetch_intents(filter)} />
                    ))
                )}
            </div>
        </div>
    );
}
