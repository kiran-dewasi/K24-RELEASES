"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Wallet, TrendingUp, CreditCard, PiggyBank, ArrowUpRight, ArrowDownRight, RefreshCw } from "lucide-react";
import { API_CONFIG, apiClient } from "@/lib/api-config";

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

interface GSTStats {
    cgst_collected: number;
    cgst_paid: number;
    sgst_collected: number;
    sgst_paid: number;
    igst_collected: number;
    igst_paid: number;
    total_liability: number;
}

interface PartyStats {
    top_customers: { name: string, value: number }[];
    top_suppliers: { name: string, value: number }[];
}

export default function DashboardStats() {
    const [stats, setStats] = useState<KPIStats | null>(null);
    const [stockStats, setStockStats] = useState<StockStats | null>(null);
    const [gstStats, setGstStats] = useState<GSTStats | null>(null);
    const [partyStats, setPartyStats] = useState<PartyStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        const fetchAll = async () => {
            setLoading(true);
            try {
                const [sRes, stRes, gRes, pRes] = await Promise.all([
                    apiClient("/api/dashboard/stats"),
                    apiClient("/api/dashboard/stock-summary"),
                    apiClient("/api/dashboard/gst-summary"),
                    apiClient("/api/dashboard/party-analysis")
                ]);

                if (sRes.ok) setStats(await sRes.json());
                if (stRes.ok) setStockStats(await stRes.json());
                if (gRes.ok) setGstStats(await gRes.json());
                if (pRes.ok) setPartyStats(await pRes.json());

            } catch (err) {
                console.error(err);
                setError("Failed to load dashboard data");
            } finally {
                setLoading(false);
            }
        };
        fetchAll();
    }, []);

    // ... existing card config ...
    const getCards = (data: KPIStats) => [
        {
            title: "Total Cash & Bank",
            value: data.cash,
            prefix: "₹",
            icon: Wallet,
            trend: "Liquid assets",
            trendUp: true,
        },
        {
            title: "Receivables",
            value: data.receivables,
            prefix: "₹",
            icon: TrendingUp,
            trend: "Pending to receive",
            trendUp: true,
        },
        {
            title: "Payables",
            value: data.payables,
            prefix: "₹",
            icon: CreditCard,
            trend: "Pending to pay",
            trendUp: false,
        },
        {
            title: "Total Sales (YTD)",
            value: data.sales,
            prefix: "₹",
            icon: PiggyBank,
            trend: "Recorded revenue",
            trendUp: true,
        }
    ];

    if (loading) {
        return (
            <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {[1, 2, 3, 4].map((i) => (
                        <div key={i} className="relative overflow-hidden rounded-xl border bg-card text-card-foreground shadow">
                            <div className="p-6 flex flex-row items-center justify-between space-y-0 pb-2">
                                <Skeleton className="h-4 w-[100px]" />
                                <Skeleton className="h-4 w-4 rounded-full" />
                            </div>
                            <div className="p-6 pt-0">
                                <Skeleton className="h-8 w-[120px] mb-1" />
                                <Skeleton className="h-3 w-[80px]" />
                            </div>
                        </div>
                    ))}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="rounded-xl border bg-card text-card-foreground shadow h-[200px] p-6">
                        <div className="space-y-2">
                            <Skeleton className="h-4 w-[150px]" />
                            <div className="pt-4  flex justify-center">
                                <Skeleton className="h-4 w-[200px]" />
                            </div>
                        </div>
                    </div>
                    <div className="rounded-xl border bg-card text-card-foreground shadow h-[200px] p-6">
                        <div className="space-y-4">
                            <Skeleton className="h-4 w-[150px]" />
                            <div className="space-y-2 pt-2">
                                <Skeleton className="h-10 w-full" />
                                <Skeleton className="h-10 w-full" />
                            </div>
                        </div>
                    </div>
                </div>

                <div className="rounded-xl border bg-card text-card-foreground shadow h-[300px] p-6">
                    <div className="space-y-4">
                        <div className="flex justify-between">
                            <div className="space-y-2">
                                <Skeleton className="h-6 w-[200px]" />
                                <Skeleton className="h-4 w-[300px]" />
                            </div>
                            <Skeleton className="h-9 w-[120px]" />
                        </div>
                        <div className="space-y-2 pt-4">
                            {[1, 2, 3, 4].map(j => <Skeleton key={j} className="h-12 w-full" />)}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    if (error || !stats) {
        return (
            <div className="p-4 bg-red-50 text-red-600 rounded-lg text-sm flex items-center gap-2">
                <RefreshCw className="h-4 w-4" /> {error || "No data available"}
            </div>
        );
    }

    const cards = getCards(stats);

    return (
        <div className="space-y-6">
            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {cards.map((card, i) => (
                    <Card key={i} className="relative overflow-hidden">
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium text-muted-foreground">
                                {card.title}
                            </CardTitle>
                            <card.icon className="h-4 w-4 text-muted-foreground opacity-70" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold tracking-tight">
                                {card.prefix}{card.value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                            </div>
                            <p className="text-xs text-muted-foreground mt-1 flex items-center">
                                <span className="text-emerald-600 flex items-center font-medium">
                                    {card.trend}
                                </span>
                            </p>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Additional Widgets Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                {/* GST Summary */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-sm font-semibold">GST Liability (This Month)</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3 flex flex-col items-center justify-center h-[120px]">
                        {/* 
                           Disabled rigid 18% GST calculation.
                           Real-time GST analysis from Vouchers coming soon.
                        */}
                        <p className="text-muted-foreground font-medium text-sm">GST Analysis Coming Soon</p>
                    </CardContent>
                </Card>

                {/* Top Parties */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-sm font-semibold">Top Performers</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div>
                            <p className="text-xs font-medium text-muted-foreground mb-2">Top Customer</p>
                            {partyStats?.top_customers?.[0] ? (
                                <div className="flex justify-between items-center bg-green-50 p-2 rounded-md">
                                    <span className="text-sm font-medium truncate w-2/3">{partyStats.top_customers[0].name}</span>
                                    <span className="text-xs font-bold text-green-700">₹{partyStats.top_customers[0].value.toLocaleString('en-IN', { compactDisplay: "short", notation: "compact" })}</span>
                                </div>
                            ) : <p className="text-xs text-muted-foreground">No Sales data</p>}
                        </div>
                        <div>
                            <p className="text-xs font-medium text-muted-foreground mb-2">Top Supplier</p>
                            {partyStats?.top_suppliers?.[0] ? (
                                <div className="flex justify-between items-center bg-blue-50 p-2 rounded-md">
                                    <span className="text-sm font-medium truncate w-2/3">{partyStats.top_suppliers[0].name}</span>
                                    <span className="text-xs font-bold text-blue-700">₹{partyStats.top_suppliers[0].value.toLocaleString('en-IN', { compactDisplay: "short", notation: "compact" })}</span>
                                </div>
                            ) : <p className="text-xs text-muted-foreground">No Purchase data</p>}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Inventory Overview Table */}
            <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                        <CardTitle className="text-lg font-semibold">Inventory Status</CardTitle>
                        <p className="text-sm text-muted-foreground mt-1">
                            Total Valuation: <span className="font-bold text-foreground">₹{(stockStats?.total_value || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
                            • Low Stock Items: <span className="font-bold text-amber-600">{stockStats?.low_stock_items || 0}</span>
                        </p>
                    </div>
                    <Button variant="outline" size="sm">View Full Inventory</Button>
                </CardHeader>
                <CardContent>
                    <div className="rounded-md border">
                        <Table>
                            <TableHeader>
                                <TableRow className="bg-muted/50">
                                    <TableHead>Item Name</TableHead>
                                    <TableHead className="text-right">Quantity</TableHead>
                                    <TableHead className="text-right">Avg Price</TableHead>
                                    <TableHead className="text-right">Total Value</TableHead>
                                    <TableHead className="w-[100px]">Status</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {stockStats?.items?.slice(0, 10).map((item, i) => (
                                    <TableRow key={i}>
                                        <TableCell className="font-medium text-foreground">{item.name}</TableCell>
                                        <TableCell className="text-right">{item.quantity.toLocaleString()}</TableCell>
                                        <TableCell className="text-right">₹{item.rate.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</TableCell>
                                        <TableCell className="text-right font-medium">₹{item.value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</TableCell>
                                        <TableCell>
                                            <Badge variant="outline" className={`font-normal whitespace-nowrap ${item.status === 'Out of Stock' ? 'bg-red-50 text-red-700 border-red-200' :
                                                item.status === 'Low Stock' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                                                    'bg-green-50 text-green-700 border-green-200'
                                                }`}>
                                                {item.status}
                                            </Badge>
                                        </TableCell>
                                    </TableRow>
                                ))}
                                {!stockStats?.items?.length && (
                                    <TableRow>
                                        <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                                            No stock items found.
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
