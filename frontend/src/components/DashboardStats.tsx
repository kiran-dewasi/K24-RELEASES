"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Wallet, TrendingUp, CreditCard, PiggyBank,
    ArrowUpRight, ArrowDownRight, RefreshCw, Zap
} from "lucide-react";
import { api } from "@/lib/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface KPIStats {
    sales: number;
    sales_change: number;
    receivables: number;
    receivables_change: number;
    payables: number;
    payables_change: number;
    cash: number;
    last_updated: string;
}

interface StockItem {
    name: string;
    quantity: number;
    rate: number;
    value: number;
    status: string;
}

interface StockStats {
    total_items: number;
    low_stock_items: number;
    total_value: number;
    items: StockItem[];
}

interface PartyStats {
    top_customers: { name: string; value: number; ledger_id: number }[];
    top_suppliers: { name: string; value: number; ledger_id: number }[];
}

function TrendBadge({ value }: { value: number }) {
    const isUp = value >= 0;
    return (
        <span className={`inline-flex items-center gap-0.5 text-xs font-semibold ${isUp ? "text-emerald-600" : "text-red-500"}`}>
            {isUp
                ? <ArrowUpRight className="h-3 w-3" />
                : <ArrowDownRight className="h-3 w-3" />
            }
            {Math.abs(value).toFixed(1)}%
        </span>
    );
}

export default function DashboardStats() {
    const [stats, setStats] = useState<KPIStats | null>(null);
    const [stockStats, setStockStats] = useState<StockStats | null>(null);
    const [partyStats, setPartyStats] = useState<PartyStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [refreshKey, setRefreshKey] = useState(0);
    const router = useRouter();

    const fetchAll = async () => {
        setLoading(true);
        setError("");
        try {
            // silent401: a 401 from the local sidecar (e.g. Tally not yet synced)
            // must NEVER trigger "Session expired" toast — return null silently instead.
            const [statsData, stockData, partyData] = await Promise.all([
                api.get("/api/dashboard/stats",        { silent401: true }),
                api.get("/api/dashboard/stock-summary",{ silent401: true }),
                api.get("/api/dashboard/party-analysis",{ silent401: true }),
            ]);

            // Guard against null (returned when local backend 401s silently)
            if (statsData) {
                setStats(statsData);
                // Auto-retry once if all financial values are 0 (backend still warming up / Tally not synced yet)
                if (statsData.cash === 0 && statsData.receivables === 0 && statsData.payables === 0) {
                    setTimeout(() => setRefreshKey(k => k + 1), 4000);
                }
            }
            if (stockData)  setStockStats(stockData);
            if (partyData)  setPartyStats(partyData);
        } catch (err) {
            console.error(err);
            setError("Failed to load dashboard data");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAll();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [refreshKey]);

    const getCards = (data: KPIStats) => [
        {
            title: "Total Cash & Bank",
            value: data.cash,
            icon: Wallet,
            change: null, // Cash doesn't have a change metric
            color: "indigo",
            description: "Liquid assets available",
        },
        {
            title: "Receivables",
            value: data.receivables,
            icon: TrendingUp,
            change: data.receivables_change,
            color: "emerald",
            description: "Pending to receive",
        },
        {
            title: "Payables",
            value: data.payables,
            icon: CreditCard,
            change: data.payables_change,
            color: "rose",
            description: "Pending to pay",
        },
        {
            title: "Total Sales (FY 2025-26)",
            value: data.sales,
            icon: PiggyBank,
            change: data.sales_change,
            color: "violet",
            description: "Apr 2025 – today",
        },
    ];

    const colorMap: Record<string, { bg: string; icon: string; badge: string }> = {
        indigo: { bg: "bg-indigo-50", icon: "text-indigo-600", badge: "bg-indigo-100 text-indigo-700" },
        emerald: { bg: "bg-emerald-50", icon: "text-emerald-600", badge: "bg-emerald-100 text-emerald-700" },
        rose: { bg: "bg-rose-50", icon: "text-rose-600", badge: "bg-rose-100 text-rose-700" },
        violet: { bg: "bg-violet-50", icon: "text-violet-600", badge: "bg-violet-100 text-violet-700" },
    };

    if (loading) {
        return (
            <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {[1, 2, 3, 4].map((i) => (
                        <Card key={i} className="relative overflow-hidden">
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <Skeleton className="h-4 w-[100px]" />
                                <Skeleton className="h-8 w-8 rounded-xl" />
                            </CardHeader>
                            <CardContent>
                                <Skeleton className="h-8 w-[120px] mb-2" />
                                <Skeleton className="h-3 w-[80px]" />
                            </CardContent>
                        </Card>
                    ))}
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <Card className="h-[160px] animate-pulse bg-slate-50" />
                    <Card className="h-[160px] animate-pulse bg-slate-50" />
                </div>
                <Card className="h-[300px] animate-pulse bg-slate-50" />
            </div>
        );
    }

    if (error || !stats) {
        return (
            <div className="p-4 bg-red-50 text-red-600 rounded-xl text-sm flex items-center gap-2 border border-red-200">
                <RefreshCw className="h-4 w-4 shrink-0" />
                {error || "No data available — sync your Tally data first."}
            </div>
        );
    }

    const cards = getCards(stats);

    return (
        <div className="space-y-6">
            {/* KPI Cards with trend deltas */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {cards.map((card, i) => {
                    const colors = colorMap[card.color];
                    return (
                        <Card key={i} className="relative overflow-hidden border-slate-200/80 hover:shadow-md transition-shadow duration-200">
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 pt-4 px-5">
                                <CardTitle className="text-sm font-medium text-slate-500">
                                    {card.title}
                                </CardTitle>
                                <div className={`h-9 w-9 rounded-xl ${colors.bg} flex items-center justify-center`}>
                                    <card.icon className={`h-4.5 w-4.5 ${colors.icon}`} />
                                </div>
                            </CardHeader>
                            <CardContent className="px-5 pb-4">
                                <div className="text-2xl font-bold tracking-tight text-slate-800">
                                    ₹{card.value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                                </div>
                                <div className="flex items-center gap-2 mt-1.5">
                                    {card.change !== null && card.change !== undefined ? (
                                        <>
                                            <TrendBadge value={card.change} />
                                            <span className="text-xs text-slate-400">{card.description}</span>
                                        </>
                                    ) : (
                                        <span className="text-xs text-slate-400">{card.description}</span>
                                    )}
                                </div>
                            </CardContent>
                            {/* Subtle accent line at top */}
                            <div className={`absolute top-0 left-0 right-0 h-0.5 ${colors.bg.replace("50", "400")}`} />
                        </Card>
                    );
                })}
            </div>

            {/* Top Parties — 2 column */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Top Customer */}
                <Card className="border-slate-200/80">
                    <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-semibold text-slate-700">Top Customer</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                        {partyStats?.top_customers?.slice(0, 3).map((c, i) => (
                            <Link key={i} href={`/parties?id=${c.ledger_id}`}>
                                <div className="flex items-center justify-between bg-emerald-50 rounded-lg px-3 py-2.5 hover:bg-emerald-100 transition-colors cursor-pointer">
                                    <div className="flex items-center gap-2.5">
                                        <div className="h-7 w-7 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-700 text-xs font-bold">
                                            {c.name.charAt(0).toUpperCase()}
                                        </div>
                                        <span className="text-sm font-medium text-slate-700 truncate max-w-[160px]">{c.name}</span>
                                    </div>
                                    <span className="text-sm font-bold text-emerald-700 shrink-0">
                                        ₹{c.value.toLocaleString("en-IN", { notation: "compact", compactDisplay: "short" })}
                                    </span>
                                </div>
                            </Link>
                        )) ?? (
                                <p className="text-sm text-slate-400 py-4 text-center">No customer data yet</p>
                            )}
                    </CardContent>
                </Card>

                {/* Top Supplier */}
                <Card className="border-slate-200/80">
                    <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-semibold text-slate-700">Top Supplier</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                        {partyStats?.top_suppliers?.slice(0, 3).map((s, i) => (
                            <Link key={i} href={`/parties?id=${s.ledger_id}`}>
                                <div className="flex items-center justify-between bg-indigo-50 rounded-lg px-3 py-2.5 hover:bg-indigo-100 transition-colors cursor-pointer">
                                    <div className="flex items-center gap-2.5">
                                        <div className="h-7 w-7 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 text-xs font-bold">
                                            {s.name.charAt(0).toUpperCase()}
                                        </div>
                                        <span className="text-sm font-medium text-slate-700 truncate max-w-[160px]">{s.name}</span>
                                    </div>
                                    <span className="text-sm font-bold text-indigo-700 shrink-0">
                                        ₹{s.value.toLocaleString("en-IN", { notation: "compact", compactDisplay: "short" })}
                                    </span>
                                </div>
                            </Link>
                        )) ?? (
                                <p className="text-sm text-slate-400 py-4 text-center">No supplier data yet</p>
                            )}
                    </CardContent>
                </Card>
            </div>

            {/* Inventory Table */}
            <Card className="border-slate-200/80">
                <CardHeader className="flex flex-row items-center justify-between pb-4">
                    <div>
                        <CardTitle className="text-base font-semibold text-slate-800">Inventory Status</CardTitle>
                        <p className="text-sm text-slate-400 mt-0.5">
                            Valuation:{" "}
                            <span className="font-semibold text-slate-700">
                                ₹{(stockStats?.total_value || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                            </span>
                            {" · "}Low Stock:{" "}
                            <span className="font-semibold text-amber-600">{stockStats?.low_stock_items || 0}</span>
                        </p>
                    </div>
                    <Button variant="outline" size="sm" onClick={() => router.push("/inventory")}
                        className="text-xs h-8 rounded-lg border-slate-200">
                        View All
                    </Button>
                </CardHeader>
                <CardContent className="pt-0">
                    <div className="rounded-xl border border-slate-100 overflow-hidden">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-slate-50/80 hover:bg-slate-50/80">
                                    <TableHead className="text-xs font-semibold text-slate-500">Item</TableHead>
                                    <TableHead className="text-right text-xs font-semibold text-slate-500">Qty</TableHead>
                                    <TableHead className="text-right text-xs font-semibold text-slate-500">Rate</TableHead>
                                    <TableHead className="text-right text-xs font-semibold text-slate-500">Value</TableHead>
                                    <TableHead className="text-xs font-semibold text-slate-500">Status</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {stockStats?.items?.slice(0, 8).map((item, i) => (
                                    <TableRow key={i} className="hover:bg-slate-50/50">
                                        <TableCell className="font-medium text-slate-700 text-sm py-3">
                                            <Link
                                                href={`/inventory?item=${encodeURIComponent(item.name)}`}
                                                className="hover:text-blue-600 hover:underline cursor-pointer transition-colors"
                                            >
                                                {item.name}
                                            </Link>
                                        </TableCell>
                                        <TableCell className="text-right text-sm text-slate-600">{item.quantity.toLocaleString()}</TableCell>
                                        <TableCell className="text-right text-sm text-slate-600">₹{item.rate.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</TableCell>
                                        <TableCell className="text-right text-sm font-semibold text-slate-700">₹{item.value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</TableCell>
                                        <TableCell>
                                            <Badge variant="outline" className={`text-[10px] font-medium py-0.5 ${item.status === "Out of Stock"
                                                ? "bg-red-50 text-red-600 border-red-200"
                                                : item.status === "Low Stock"
                                                    ? "bg-amber-50 text-amber-700 border-amber-200"
                                                    : "bg-emerald-50 text-emerald-700 border-emerald-200"
                                                }`}>
                                                {item.status}
                                            </Badge>
                                        </TableCell>
                                    </TableRow>
                                ))}
                                {!stockStats?.items?.length && (
                                    <TableRow>
                                        <TableCell colSpan={5} className="h-24 text-center text-sm text-slate-400">
                                            No stock data — sync from Tally first.
                                        </TableCell>
                                    </TableRow>
                                )}
                            </TableBody>
                        </Table>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
