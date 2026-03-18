"use client";

import { Suspense, useState, useCallback, useEffect } from "react";
import { KittuInsightBar } from "@/components/reports/KittuInsightBar";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Download, SlidersHorizontal, Loader2, TrendingUp, TrendingDown, Scale, Wallet, Clock, RefreshCw, Search } from "lucide-react";
import Link from 'next/link';
import { Badge } from "@/components/ui/badge";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from "recharts";
import { apiRequest } from "@/lib/api";

// ─── Report config map ─────────────────────────────────────────────────────────
interface ReportConfig {
    title: string;
    subtitle: string;
    apiPath: string;
    defaultVoucherTypes: string[];
    availableVoucherTypes: string[];
    summaryKeys: string[];
    chartDataKey: string;
    chartColor: string;
    tableColumns: { key: string; label: string; align?: "right" }[];
    isComingSoon?: boolean;
}

const REPORT_CONFIGS: Record<string, ReportConfig> = {
    "sales-register": {
        title: "Sales Register",
        subtitle: "All sales transactions with filters",
        apiPath: "/reports/sales-register",
        defaultVoucherTypes: ["Sales", "Credit Note"],
        availableVoucherTypes: ["Sales", "Credit Note"],
        summaryKeys: ["total_amount", "total_count", "tax_estimate"],
        chartDataKey: "total_amount",
        chartColor: "#3B82F6",
        tableColumns: [
            { key: "date", label: "Date" },
            { key: "party_name", label: "Party Name" },
            { key: "voucher_type", label: "Voucher Type" },
            { key: "voucher_no", label: "Voucher No." },
            { key: "amount", label: "Amount", align: "right" },
        ],
    },
    "purchase-register": {
        title: "Purchase Register",
        subtitle: "All purchase transactions with filters",
        apiPath: "/reports/purchase-register",
        defaultVoucherTypes: ["Purchase", "Debit Note"],
        availableVoucherTypes: ["Purchase", "Debit Note"],
        summaryKeys: ["total_amount", "total_count"],
        chartDataKey: "total_amount",
        chartColor: "#F97316",
        tableColumns: [
            { key: "date", label: "Date" },
            { key: "party_name", label: "Party Name" },
            { key: "voucher_type", label: "Voucher Type" },
            { key: "voucher_no", label: "Voucher No." },
            { key: "amount", label: "Amount", align: "right" },
        ],
    },
    "cash-flow": {
        title: "Cash Flow",
        subtitle: "Inflows & outflows summary",
        apiPath: "/reports/cash-flow",
        defaultVoucherTypes: [],
        availableVoucherTypes: [],
        summaryKeys: ["total_inflow", "total_outflow", "net_flow"],
        chartDataKey: "total_amount",
        chartColor: "#10B981",
        tableColumns: [
            { key: "date", label: "Date" },
            { key: "party_name", label: "Party Name" },
            { key: "voucher_type", label: "Type" },
            { key: "direction", label: "Direction" },
            { key: "amount", label: "Amount", align: "right" },
        ],
    },
    "balance-sheet": {
        title: "Balance Sheet",
        subtitle: "Assets vs Liabilities snapshot",
        apiPath: "/reports/balance-sheet",
        defaultVoucherTypes: [],
        availableVoucherTypes: [],
        summaryKeys: ["total_assets", "total_liabilities", "net_difference"],
        chartDataKey: "amount",
        chartColor: "#8B5CF6",
        tableColumns: [
            { key: "name", label: "Ledger Name" },
            { key: "group", label: "Group" },
            { key: "amount", label: "Amount", align: "right" },
        ],
    },
    "profit-loss": {
        title: "Profit & Loss",
        subtitle: "Income vs Expense analysis",
        apiPath: "/reports/profit-loss",
        defaultVoucherTypes: [],
        availableVoucherTypes: [],
        summaryKeys: ["total_income", "total_expenses", "net_profit"],
        chartDataKey: "total_amount",
        chartColor: "#EF4444",
        tableColumns: [
            { key: "name", label: "Account" },
            { key: "amount", label: "Amount", align: "right" },
        ],
    },
    "gst-summary": {
        title: "GST Summary",
        subtitle: "GSTR reconciliation dashboard",
        apiPath: "",
        defaultVoucherTypes: [],
        availableVoucherTypes: [],
        summaryKeys: [],
        chartDataKey: "",
        chartColor: "#6366F1",
        tableColumns: [],
        isComingSoon: true,
    },
};

// ─── Filter State ──────────────────────────────────────────────────────────────
interface FilterState {
    dateRange: string;
    dateFrom: string;
    dateTo: string;
    voucherTypes: string[];
    partyName: string;
}

function getDefaultDates(): { from: string; to: string } {
    const now = new Date();
    const fyStartYear = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1;
    return {
        from: `${fyStartYear}-04-01`,
        to: `${fyStartYear + 1}-03-31`,
    };
}

function dateRangeToIso(range: string): { from: string; to: string } {
    const now = new Date();
    const y = now.getFullYear();
    const m = now.getMonth();

    switch (range) {
        case "this_month": {
            const start = new Date(y, m, 1);
            const end = new Date(y, m + 1, 0);
            return { from: start.toISOString().slice(0, 10), to: end.toISOString().slice(0, 10) };
        }
        case "last_month": {
            const start = new Date(y, m - 1, 1);
            const end = new Date(y, m, 0);
            return { from: start.toISOString().slice(0, 10), to: end.toISOString().slice(0, 10) };
        }
        case "this_quarter": {
            const qStart = Math.floor(m / 3) * 3;
            const start = new Date(y, qStart, 1);
            const end = new Date(y, qStart + 3, 0);
            return { from: start.toISOString().slice(0, 10), to: end.toISOString().slice(0, 10) };
        }
        case "this_fy":
        default:
            return getDefaultDates();
    }
}

function fmt(n: number) {
    return `₹${Math.abs(n).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

// ─── Summary Cards ─────────────────────────────────────────────────────────────
function SummaryCard({ label, value, icon: Icon, color }: {
    label: string; value: string; icon: any; color: string;
}) {
    return (
        <div className="bg-white rounded-xl border p-4 flex items-center gap-4 shadow-sm">
            <div className={`p-2 rounded-lg ${color}`}>
                <Icon className="h-5 w-5 text-white" />
            </div>
            <div>
                <p className="text-xs text-muted-foreground font-medium">{label}</p>
                <p className="text-xl font-bold">{value}</p>
            </div>
        </div>
    );
}

// ─── Coming Soon Placeholder ───────────────────────────────────────────────────
function ComingSoonPlaceholder({ title }: { title: string }) {
    return (
        <div className="flex flex-col items-center justify-center h-full min-h-[400px] gap-4 text-center">
            <div className="p-5 bg-indigo-50 rounded-full">
                <Clock className="h-10 w-10 text-indigo-400" />
            </div>
            <h2 className="text-xl font-semibold text-gray-800">{title} — Coming Soon</h2>
            <p className="text-muted-foreground text-sm max-w-sm">
                We&apos;re building a full GSTR-1, 2A/2B and 3B reconciliation dashboard.
                This will be available in the next update.
            </p>
            <Badge variant="secondary" className="text-indigo-600 bg-indigo-50 border-indigo-200">
                Under Development
            </Badge>
        </div>
    );
}

// ─── Main Content ──────────────────────────────────────────────────────────────
function ReportDetailContent({ slug }: { slug: string }) {
    const config = REPORT_CONFIGS[slug] ?? REPORT_CONFIGS["sales-register"];

    const defaults = getDefaultDates();
    const [filters, setFilters] = useState<FilterState>({
        dateRange: "this_fy",
        dateFrom: defaults.from,
        dateTo: defaults.to,
        voucherTypes: config.defaultVoucherTypes,
        partyName: "",
    });

    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchData = useCallback(async (f: FilterState) => {
        if (!config.apiPath) return;
        setLoading(true);
        setError(null);
        try {
            const params = new URLSearchParams();
            if (f.dateFrom) params.set("date_from", f.dateFrom);
            if (f.dateTo) params.set("date_to", f.dateTo);
            if (f.voucherTypes.length > 0) params.set("voucher_types", f.voucherTypes.join(","));
            if (f.partyName) params.set("party_name", f.partyName);

            const result = await apiRequest(`${config.apiPath}?${params.toString()}`);
            setData(result);
        } catch (e: any) {
            setError(e.message || "Failed to load data");
        } finally {
            setLoading(false);
        }
    }, [config.apiPath]);

    // Initial load
    useEffect(() => {
        if (!config.isComingSoon) {
            fetchData(filters);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [slug]);

    const handleDateRangeChange = (val: string) => {
        if (val === "custom") {
            setFilters(prev => ({ ...prev, dateRange: "custom" }));
        } else {
            const { from, to } = dateRangeToIso(val);
            setFilters(prev => ({ ...prev, dateRange: val, dateFrom: from, dateTo: to }));
        }
    };

    const toggleVoucherType = (vtype: string) => {
        setFilters(prev => {
            const exists = prev.voucherTypes.includes(vtype);
            return {
                ...prev,
                voucherTypes: exists
                    ? prev.voucherTypes.filter(v => v !== vtype)
                    : [...prev.voucherTypes, vtype],
            };
        });
    };

    const handleApply = () => fetchData(filters);

    const handleExport = async () => {
        if (!data) return;
        const params = new URLSearchParams({ slug });
        if (filters.dateFrom) params.set("date_from", filters.dateFrom);
        if (filters.dateTo) params.set("date_to", filters.dateTo);
        if (filters.voucherTypes.length) params.set("voucher_types", filters.voucherTypes.join(","));
        if (filters.partyName) params.set("party_name", filters.partyName);

        try {
            // Call the python backend directly, passing the API key
            const backendUrl = `${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001'}/reports/${slug}/export?${params.toString()}`;
            const res = await fetch(backendUrl, {
                headers: { "x-api-key": process.env.NEXT_PUBLIC_API_KEY || "k24-secret-key-123" }
            });
            if (!res.ok) {
                const errJson = await res.json().catch(() => ({ error: res.statusText }));
                throw new Error(errJson?.error || `HTTP ${res.status}`);
            }
            const blob = await res.blob();
            const objUrl = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = objUrl;
            a.download = `k24-${slug}-${new Date().toISOString().slice(0, 10)}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(objUrl);
        } catch (err: any) {
            console.error("PDF export error:", err?.message || err);
            alert(`Export failed: ${err?.message || "Unknown error — check the backend is running."}`);
        }
    };

    const handleReset = () => {
        const f: FilterState = {
            dateRange: "this_fy",
            dateFrom: defaults.from,
            dateTo: defaults.to,
            voucherTypes: config.defaultVoucherTypes,
            partyName: "",
        };
        setFilters(f);
        fetchData(f);
    };

    // ── Derive summary cards from data ──
    const summaryCards = () => {
        if (!data) return [];
        if (slug === "sales-register") return [
            { label: "Total Sales", value: fmt(data.total_amount ?? 0), icon: TrendingUp, color: "bg-blue-500" },
            { label: "Transactions", value: String(data.total_count ?? 0), icon: SlidersHorizontal, color: "bg-slate-500" },
            { label: "Est. Tax (18%)", value: fmt(data.tax_estimate ?? 0), icon: Download, color: "bg-green-500" },
        ];
        if (slug === "purchase-register") return [
            { label: "Total Purchases", value: fmt(data.total_amount ?? 0), icon: TrendingDown, color: "bg-orange-500" },
            { label: "Transactions", value: String(data.total_count ?? 0), icon: SlidersHorizontal, color: "bg-slate-500" },
        ];
        if (slug === "cash-flow") return [
            { label: "Total Inflow", value: fmt(data.total_inflow ?? 0), icon: TrendingUp, color: "bg-green-500" },
            { label: "Total Outflow", value: fmt(data.total_outflow ?? 0), icon: TrendingDown, color: "bg-red-500" },
            { label: "Net Cash Flow", value: fmt(data.net_flow ?? 0), icon: Wallet, color: (data.net_flow ?? 0) >= 0 ? "bg-green-600" : "bg-red-600" },
        ];
        if (slug === "balance-sheet") return [
            { label: "Total Assets", value: fmt(data.total_assets ?? 0), icon: TrendingUp, color: "bg-green-500" },
            { label: "Total Liabilities", value: fmt(data.total_liabilities ?? 0), icon: Scale, color: "bg-red-500" },
            { label: "Difference", value: fmt(data.net_difference ?? 0), icon: Scale, color: Math.abs(data.net_difference ?? 0) < 1 ? "bg-green-600" : "bg-yellow-500" },
        ];
        if (slug === "profit-loss") return [
            { label: "Total Income", value: fmt(data.total_income ?? 0), icon: TrendingUp, color: "bg-green-500" },
            { label: "Total Expenses", value: fmt(data.total_expenses ?? 0), icon: TrendingDown, color: "bg-red-500" },
            { label: "Net Profit", value: fmt(data.net_profit ?? 0), icon: Wallet, color: (data.net_profit ?? 0) >= 0 ? "bg-green-600" : "bg-red-600" },
        ];
        return [];
    };

    // ── Derive table rows from data ──
    const tableRows = (): any[] => {
        if (!data) return [];
        if (["sales-register", "purchase-register", "cash-flow"].includes(slug)) {
            return data.vouchers ?? [];
        }
        if (slug === "balance-sheet") {
            return [
                ...(data.assets ?? []).map((i: any) => ({ ...i, _section: "Asset" })),
                ...(data.liabilities ?? []).map((i: any) => ({ ...i, _section: "Liability" })),
            ];
        }
        if (slug === "profit-loss") {
            const rows: any[] = [];
            for (const [k, v] of Object.entries(data.income ?? {})) {
                rows.push({ name: k, amount: v, _section: "Income" });
            }
            for (const [k, v] of Object.entries(data.expenses ?? {})) {
                rows.push({ name: k, amount: v, _section: "Expense" });
            }
            return rows;
        }
        return [];
    };

    const chartData = data?.monthly_data ?? (slug === "balance-sheet"
        ? [...(data?.assets ?? []).slice(0, 8)]
        : []);

    return (
        <div className="flex flex-col h-[calc(100vh-8rem)]">
            {/* Breadcrumb */}
            <div className="flex items-center gap-2 text-muted-foreground text-sm mb-4">
                <Link href="/reports" className="hover:text-foreground transition-colors">Reports</Link>
                <span>/</span>
                <span className="text-foreground font-medium">{config.title}</span>
            </div>

            {/* Page Header */}
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight">{config.title}</h1>
                    <p className="text-sm text-muted-foreground mt-0.5">{config.subtitle}</p>
                </div>
                <div className="flex items-center gap-2">
                    {!config.isComingSoon && <KittuInsightBar context={config.title} />}
                    <div className="h-6 w-px bg-border mx-1" />
                    <Button
                        variant="outline"
                        size="sm"
                        className="gap-2"
                        disabled={config.isComingSoon || !data || tableRows().length === 0}
                        onClick={handleExport}
                    >
                        <Download className="h-4 w-4" /> Export PDF
                    </Button>
                </div>
            </div>

            {config.isComingSoon ? (
                <ComingSoonPlaceholder title={config.title} />
            ) : (
                <div className="flex-1 flex gap-5 overflow-hidden">
                    {/* ── Left Filter Pane ── */}
                    <Card className="w-60 flex-shrink-0 flex flex-col h-full shadow-sm">
                        <div className="p-4 border-b flex items-center justify-between">
                            <span className="font-semibold text-sm flex items-center gap-2">
                                <SlidersHorizontal className="h-4 w-4" /> Filters
                            </span>
                            <Button variant="ghost" size="sm" className="h-6 text-xs text-muted-foreground" onClick={handleReset}>
                                Reset
                            </Button>
                        </div>

                        <div className="flex-1 overflow-y-auto p-4 space-y-5">
                            {/* Date Range */}
                            <div className="space-y-2">
                                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                                    Date Range
                                </label>
                                <Select value={filters.dateRange} onValueChange={handleDateRangeChange}>
                                    <SelectTrigger className="w-full bg-white text-sm">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="this_fy">This Financial Year</SelectItem>
                                        <SelectItem value="this_month">This Month</SelectItem>
                                        <SelectItem value="last_month">Last Month</SelectItem>
                                        <SelectItem value="this_quarter">This Quarter</SelectItem>
                                        <SelectItem value="custom">Custom Range</SelectItem>
                                    </SelectContent>
                                </Select>

                                {filters.dateRange === "custom" && (
                                    <div className="space-y-2 pt-1">
                                        <div>
                                            <label className="text-xs text-muted-foreground">From</label>
                                            <input
                                                type="date"
                                                value={filters.dateFrom}
                                                onChange={e => setFilters(prev => ({ ...prev, dateFrom: e.target.value }))}
                                                className="w-full mt-1 text-sm px-2 py-1.5 border border-input rounded-md focus:outline-none focus:ring-1 focus:ring-ring"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-xs text-muted-foreground">To</label>
                                            <input
                                                type="date"
                                                value={filters.dateTo}
                                                onChange={e => setFilters(prev => ({ ...prev, dateTo: e.target.value }))}
                                                className="w-full mt-1 text-sm px-2 py-1.5 border border-input rounded-md focus:outline-none focus:ring-1 focus:ring-ring"
                                            />
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Voucher Types */}
                            {config.availableVoucherTypes.length > 0 && (
                                <div className="space-y-2">
                                    <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                                        Voucher Type
                                    </label>
                                    <div className="space-y-2">
                                        {config.availableVoucherTypes.map(vtype => (
                                            <div key={vtype} className="flex items-center gap-2">
                                                <Checkbox
                                                    id={`vt-${vtype}`}
                                                    checked={filters.voucherTypes.includes(vtype)}
                                                    onCheckedChange={() => toggleVoucherType(vtype)}
                                                />
                                                <label htmlFor={`vt-${vtype}`} className="text-sm font-medium cursor-pointer">
                                                    {vtype}
                                                </label>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Party Search */}
                            {["sales-register", "purchase-register"].includes(slug) && (
                                <div className="space-y-2">
                                    <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                                        Search Party
                                    </label>
                                    <div className="relative">
                                        <input
                                            type="text"
                                            placeholder="Party name..."
                                            value={filters.partyName}
                                            onChange={e => setFilters(prev => ({ ...prev, partyName: e.target.value }))}
                                            onKeyDown={e => e.key === "Enter" && handleApply()}
                                            className="w-full text-sm pl-2 pr-8 py-1.5 border border-input rounded-md focus:outline-none focus:ring-1 focus:ring-ring"
                                        />
                                        <Search className="h-3.5 w-3.5 absolute right-2 top-2 text-muted-foreground pointer-events-none" />
                                    </div>
                                    {filters.partyName && (
                                        <button
                                            onClick={() => {
                                                setFilters(prev => ({ ...prev, partyName: "" }));
                                                fetchData({ ...filters, partyName: "" });
                                            }}
                                            className="text-xs text-muted-foreground hover:text-foreground"
                                        >
                                            ✕ Clear search
                                        </button>
                                    )}
                                </div>
                            )}
                        </div>

                        <div className="p-4 border-t">
                            <Button className="w-full gap-2" onClick={handleApply} disabled={loading}>
                                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                                Apply Filters
                            </Button>
                        </div>
                    </Card>

                    {/* ── Right Data Pane ── */}
                    <div className="flex-1 flex flex-col gap-4 overflow-hidden">
                        {/* Summary KPI Cards */}
                        {!loading && data && (
                            <div className="grid grid-cols-2 xl:grid-cols-3 gap-3 flex-shrink-0">
                                {summaryCards().map((card, i) => (
                                    <SummaryCard key={i} {...card} />
                                ))}
                            </div>
                        )}

                        {/* Chart + Table Container */}
                        <div className="flex-1 flex flex-col overflow-hidden bg-white rounded-xl border shadow-sm">
                            {/* Toolbar */}
                            <div className="h-11 border-b flex items-center px-4 justify-between bg-muted/5 flex-shrink-0">
                                <div className="flex items-center gap-2">
                                    {loading ? (
                                        <Badge variant="secondary" className="gap-1.5">
                                            <Loader2 className="h-3 w-3 animate-spin" /> Loading...
                                        </Badge>
                                    ) : (
                                        <Badge variant="secondary" className="font-normal text-muted-foreground">
                                            {tableRows().length} Records Found
                                        </Badge>
                                    )}
                                </div>
                                <div className="text-xs text-muted-foreground">
                                    {filters.dateFrom} → {filters.dateTo}
                                </div>
                            </div>

                            {error && (
                                <div className="p-4 text-sm text-red-600 bg-red-50 border-b border-red-100">
                                    ⚠️ {error} — is Tally synced?
                                </div>
                            )}

                            {/* Chart */}
                            {!loading && chartData.length > 0 && (
                                <div className="h-36 border-b px-4 pt-3 flex-shrink-0">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <BarChart data={chartData} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                                            <XAxis
                                                dataKey="month_name"
                                                axisLine={false}
                                                tickLine={false}
                                                tick={{ fontSize: 10, fill: "#94a3b8" }}
                                            />
                                            <YAxis hide />
                                            <Tooltip
                                                cursor={{ fill: "#f1f5f9" }}
                                                contentStyle={{ borderRadius: 8, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)", fontSize: 12 }}
                                                formatter={(val: any) => [`₹${Number(val).toLocaleString("en-IN")}`, "Amount"]}
                                            />
                                            <Bar dataKey={config.chartDataKey} fill={config.chartColor} radius={[3, 3, 0, 0]} barSize={20}>
                                                {chartData.map((_: any, i: number) => (
                                                    <Cell key={i} fill={config.chartColor} fillOpacity={0.7 + (i % 3) * 0.1} />
                                                ))}
                                            </Bar>
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            )}

                            {/* Loading State */}
                            {loading && (
                                <div className="flex-1 flex items-center justify-center">
                                    <div className="flex flex-col items-center gap-3 text-muted-foreground">
                                        <Loader2 className="h-8 w-8 animate-spin" />
                                        <span className="text-sm">Fetching data...</span>
                                    </div>
                                </div>
                            )}

                            {/* Empty State */}
                            {!loading && !error && tableRows().length === 0 && (
                                <div className="flex-1 flex items-center justify-center">
                                    <div className="text-center text-muted-foreground">
                                        <p className="font-medium text-sm">No records found</p>
                                        <p className="text-xs mt-1">Try changing the date range or filters, or sync Tally first.</p>
                                    </div>
                                </div>
                            )}

                            {/* Data Table */}
                            {!loading && tableRows().length > 0 && (
                                <div className="flex-1 overflow-auto">
                                    <table className="w-full text-sm text-left">
                                        <thead className="bg-muted/30 sticky top-0 z-10 text-xs uppercase text-muted-foreground font-semibold">
                                            <tr>
                                                {config.tableColumns.map(col => (
                                                    <th
                                                        key={col.key}
                                                        className={`px-4 py-3 ${col.align === "right" ? "text-right" : ""}`}
                                                    >
                                                        {col.label}
                                                    </th>
                                                ))}
                                                {/* Section badge for balance sheet / p&l */}
                                                {["balance-sheet", "profit-loss"].includes(slug) && (
                                                    <th className="px-4 py-3">Category</th>
                                                )}
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-border/50">
                                            {tableRows().map((row: any, i: number) => (
                                                <tr key={row.id ?? i} className="hover:bg-muted/10 transition-colors">
                                                    {config.tableColumns.map(col => {
                                                        const val = row[col.key];
                                                        const isAmount = col.align === "right";
                                                        const isDirection = col.key === "direction";
                                                        return (
                                                            <td
                                                                key={col.key}
                                                                className={`px-4 py-2.5 ${isAmount ? "text-right font-medium" : "text-muted-foreground"}`}
                                                            >
                                                                {isAmount ? (
                                                                    <span className="text-foreground">
                                                                        ₹{Number(val ?? 0).toLocaleString("en-IN")}
                                                                    </span>
                                                                ) : isDirection ? (
                                                                    <Badge
                                                                        variant="secondary"
                                                                        className={val === "inflow"
                                                                            ? "text-green-700 bg-green-50"
                                                                            : "text-red-700 bg-red-50"}
                                                                    >
                                                                        {val === "inflow" ? "↑ In" : "↓ Out"}
                                                                    </Badge>
                                                                ) : (col.key === "party_name" || col.key === "name") && row.ledger_id ? (
                                                                    <Link
                                                                        href={`/parties?id=${row.ledger_id}`}
                                                                        className="text-foreground font-medium hover:underline hover:text-primary transition-colors"
                                                                        onClick={(e) => e.stopPropagation()}
                                                                    >
                                                                        {val ?? "—"}
                                                                    </Link>
                                                                ) : (
                                                                    <span className={col.key === "party_name" || col.key === "name" ? "text-foreground font-medium" : ""}>
                                                                        {val ?? "—"}
                                                                    </span>
                                                                )}
                                                            </td>
                                                        );
                                                    })}
                                                    {["balance-sheet", "profit-loss"].includes(slug) && (
                                                        <td className="px-4 py-2.5">
                                                            <Badge
                                                                variant="outline"
                                                                className={
                                                                    row._section === "Asset" || row._section === "Income"
                                                                        ? "text-green-700 border-green-200"
                                                                        : "text-red-700 border-red-200"
                                                                }
                                                            >
                                                                {row._section}
                                                            </Badge>
                                                        </td>
                                                    )}
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

// ─── Export ────────────────────────────────────────────────────────────────────
interface ReportDetailPageProps {
    slug: string;
}

export default function ReportDetailPage({ slug }: ReportDetailPageProps) {
    return (
        <Suspense
            fallback={
                <div className="flex h-[calc(100vh-8rem)] items-center justify-center">
                    <Loader2 className="animate-spin h-8 w-8 text-muted-foreground" />
                </div>
            }
        >
            <ReportDetailContent slug={slug} />
        </Suspense>
    );
}
