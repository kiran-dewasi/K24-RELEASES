"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { AreaChart, Area, ResponsiveContainer } from "recharts";
import { Loader2 } from "lucide-react";

interface Stats {
    collected: number;
    overdue: number;
    chartData: Array<{ value: number }>;
}

export function InvoiceStats() {
    const [stats, setStats] = useState<Stats>({ collected: 0, overdue: 0, chartData: [] });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchStats = async () => {
            try {
                // Fetch dashboard stats which includes receivables
                const statsRes = await api.get("/api/dashboard/stats");
                const dashStats = statsRes.ok ? await statsRes.json() : null;

                // Fetch cashflow for chart
                const cfRes = await api.get("/api/dashboard/cashflow");
                const cashflowData = cfRes.ok ? await cfRes.json() : [];

                // Convert cashflow to chart format
                const chartData = cashflowData.slice(-7).map((d: any) => ({
                    value: Math.abs(d.value || 0)
                }));

                // If no real data, use placeholder
                if (chartData.length === 0) {
                    for (let i = 0; i < 7; i++) {
                        chartData.push({ value: Math.random() * 1000 + 200 });
                    }
                }

                setStats({
                    collected: dashStats?.sales || 0,
                    overdue: dashStats?.receivables || 0,
                    chartData
                });
            } catch (error) {
                console.error("Failed to fetch invoice stats", error);
                // Set fallback data
                setStats({
                    collected: 0,
                    overdue: 0,
                    chartData: [
                        { value: 400 }, { value: 300 }, { value: 500 },
                        { value: 200 }, { value: 700 }, { value: 600 }, { value: 900 }
                    ]
                });
            } finally {
                setLoading(false);
            }
        };

        fetchStats();
    }, []);

    const totalVolume = stats.collected + stats.overdue;

    if (loading) {
        return (
            <Card className="h-full bg-slate-900 text-white border-none shadow-md flex items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
            </Card>
        );
    }

    const formatAmount = (amount: number) => {
        if (amount >= 10000000) {  // 1 Crore
            return `₹${(amount / 10000000).toFixed(1)}Cr`;
        } else if (amount >= 100000) {  // 1 Lakh
            return `₹${(amount / 100000).toFixed(1)}L`;
        } else if (amount >= 1000) {
            return `₹${(amount / 1000).toFixed(1)}k`;
        }
        return `₹${amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
    };

    return (
        <Card className="h-full bg-slate-900 text-white border-none shadow-md">
            <CardContent className="p-6 h-full flex items-center justify-between">
                <div className="space-y-1">
                    <p className="text-slate-400 text-xs font-medium uppercase tracking-wider">Total Volume</p>
                    <div className="text-2xl font-bold">
                        {formatAmount(totalVolume)}
                    </div>
                    <div className="flex gap-4 text-xs mt-2">
                        <span className="text-emerald-400 flex items-center gap-1">
                            ● {formatAmount(stats.collected)} Sales
                        </span>
                        <span className="text-amber-400 flex items-center gap-1">
                            ● {formatAmount(stats.overdue)} Receivable
                        </span>
                    </div>
                </div>
                <div className="h-16 w-32 opacity-50">
                    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                        <AreaChart data={stats.chartData}>
                            <Area
                                type="monotone"
                                dataKey="value"
                                stroke="#34d399"
                                fill="#34d399"
                                fillOpacity={0.2}
                                strokeWidth={2}
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </CardContent>
        </Card>
    );
}
