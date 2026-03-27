"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";

export function DashboardCharts() {
    const [cashflowData, setCashflowData] = useState<any[]>([]);
    const [receivablesData, setReceivablesData] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                // silent401: 401 from local sidecar must NOT trigger "Session expired" toast
                const [cfRes, recRes] = await Promise.all([
                    api.get("/api/dashboard/cashflow",   { silent401: true }),
                    api.get("/api/dashboard/receivables", { silent401: true })
                ]);

                // api.get returns parsed JSON (or null on silent 401)
                if (cfRes)  setCashflowData(cfRes);
                if (recRes) setReceivablesData(recRes);
            } catch (error) {
                console.error("Failed to fetch chart data", error);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    const EmptyState = ({ message }: { message: string }) => (
        <div className="flex h-full w-full flex-col items-center justify-center gap-2 text-muted-foreground">
            <div className="rounded-full bg-muted p-3">
                <CartesianGrid className="h-6 w-6 opacity-50" />
            </div>
            <p className="text-sm font-medium">{message}</p>
        </div>
    );

    if (loading) {
        return (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card className="animate-pulse h-[400px] bg-slate-50" />
                <Card className="animate-pulse h-[400px] bg-slate-50" />
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Cashflow Chart */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base font-semibold">Cashflow (Last 90 Days)</CardTitle>
                    <CardDescription>Net cash movement calculated from receipts & payments</CardDescription>
                </CardHeader>
                <CardContent>
                    {cashflowData.length > 0 ? (
                        <div style={{ width: '100%', height: 300 }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={cashflowData}>
                                    <defs>
                                        <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.3} />
                                            <stop offset="95%" stopColor="var(--primary)" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border)" />
                                    <XAxis
                                        dataKey="date"
                                        tickLine={false}
                                        axisLine={false}
                                        tick={{ fontSize: 12, fill: "var(--muted-foreground)" }}
                                        tickMargin={10}
                                    />
                                    <YAxis
                                        tickLine={false}
                                        axisLine={false}
                                        tick={{ fontSize: 12, fill: "var(--muted-foreground)" }}
                                        tickFormatter={(value) => `₹${value / 1000}k`}
                                    />
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: "var(--background)",
                                            border: "1px solid var(--border)",
                                            borderRadius: "8px",
                                            fontSize: "12px"
                                        }}
                                        formatter={(value) => [`₹${(Number(value) || 0).toLocaleString()}`, "Amount"]}
                                    />
                                    <Area
                                        type="monotone"
                                        dataKey="value"
                                        stroke="var(--primary)"
                                        strokeWidth={2}
                                        fillOpacity={1}
                                        fill="url(#colorValue)"
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    ) : (
                        <EmptyState message="No cashflow data available yet" />
                    )}
                </CardContent>
            </Card>

            {/* Receivables Bar Chart */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base font-semibold">Top Receivables</CardTitle>
                    <CardDescription>Highest outstanding amounts by customer</CardDescription>
                </CardHeader>
                <CardContent>
                    {receivablesData.length > 0 ? (
                        <div style={{ width: '100%', height: 300 }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={receivablesData} layout="vertical" margin={{ left: 0, right: 30 }}>
                                    <CartesianGrid horizontal={false} strokeDasharray="3 3" stroke="var(--border)" />
                                    <XAxis
                                        type="number"
                                        hide
                                    />
                                    <YAxis
                                        dataKey="name"
                                        type="category"
                                        tickLine={false}
                                        axisLine={false}
                                        width={100}
                                        tick={{ fontSize: 12, fill: "var(--foreground)", fontWeight: 500 }}
                                    />
                                    <Tooltip
                                        cursor={{ fill: 'transparent' }}
                                        contentStyle={{
                                            backgroundColor: "var(--background)",
                                            border: "1px solid var(--border)",
                                            borderRadius: "8px",
                                            fontSize: "12px"
                                        }}
                                        formatter={(value) => [`₹${(Number(value) || 0).toLocaleString()}`, "Outstanding"]}
                                    />
                                    <Bar
                                        dataKey="amount"
                                        fill="var(--chart-2)"
                                        radius={[0, 4, 4, 0]}
                                        barSize={32}
                                    />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    ) : (
                        <EmptyState message="No outstanding receivables found" />
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
