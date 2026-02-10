"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, TrendingDown, FileText, Calendar, ShoppingCart } from "lucide-react";
import Link from "next/link";
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip } from "recharts";

interface MonthlyData {
    month_num: number;
    month_name: string;
    total_amount: number;
    voucher_count: number;
}

interface PurchaseReport {
    year: number;
    total_purchase: number;
    monthly_data: MonthlyData[];
}

export default function PurchaseRegisterPage() {
    const [data, setData] = useState<PurchaseReport | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch("http://127.0.0.1:8000/reports/purchase-register", {
            headers: { "x-api-key": "k24-secret-key-123" }
        })
            .then(res => res.json())
            .then(setData)
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 p-8 flex items-center justify-center">
                <div className="animate-pulse flex flex-col items-center gap-4">
                    <div className="h-12 w-12 bg-gray-200 rounded-full"></div>
                    <div className="h-4 w-32 bg-gray-200 rounded"></div>
                </div>
            </div>
        );
    }

    if (!data) return <div>Error loading report</div>;

    const avgTicket = data.total_purchase / (data.monthly_data.reduce((acc, curr) => acc + curr.voucher_count, 0) || 1);

    return (
        <div className="min-h-screen bg-[#FAFAF8] text-[#1A1A1A] font-sans">
            {/* Header */}
            <header className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-gray-200 px-6 py-4">
                <div className="max-w-6xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link href="/" className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                            <ArrowLeft className="h-5 w-5 text-gray-500" />
                        </Link>
                        <div>
                            <h1 className="text-xl font-semibold tracking-tight">Purchase Register</h1>
                            <p className="text-xs text-gray-500">Financial Year {data.year}-{data.year + 1}</p>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <button className="px-3 py-1.5 text-sm font-medium bg-black text-white rounded-md hover:bg-gray-800 transition-colors">
                            Export PDF
                        </button>
                    </div>
                </div>
            </header>

            <main className="max-w-6xl mx-auto px-6 py-8 space-y-8">
                {/* KPI Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Card className="border-none shadow-sm bg-white">
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm font-medium text-gray-500">Total Purchases</CardTitle>
                            <ShoppingCart className="h-4 w-4 text-orange-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">₹{data.total_purchase.toLocaleString('en-IN')}</div>
                            <p className="text-xs text-gray-500 mt-1">Total expenses</p>
                        </CardContent>
                    </Card>
                    <Card className="border-none shadow-sm bg-white">
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm font-medium text-gray-500">Total Vouchers</CardTitle>
                            <FileText className="h-4 w-4 text-blue-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{data.monthly_data.reduce((acc, curr) => acc + curr.voucher_count, 0)}</div>
                            <p className="text-xs text-gray-500 mt-1">Bills recorded</p>
                        </CardContent>
                    </Card>
                    <Card className="border-none shadow-sm bg-white">
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm font-medium text-gray-500">Avg. Bill Value</CardTitle>
                            <Calendar className="h-4 w-4 text-purple-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">₹{Math.round(avgTicket).toLocaleString('en-IN')}</div>
                            <p className="text-xs text-gray-500 mt-1">Per purchase average</p>
                        </CardContent>
                    </Card>
                </div>

                {/* Chart Section */}
                <Card className="border-none shadow-sm bg-white">
                    <CardHeader>
                        <CardTitle className="text-base font-medium">Monthly Trends</CardTitle>
                    </CardHeader>
                    <CardContent className="h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={data.monthly_data}>
                                <XAxis
                                    dataKey="month_name"
                                    axisLine={false}
                                    tickLine={false}
                                    tick={{ fontSize: 12, fill: '#888' }}
                                    tickFormatter={(val: string) => val.slice(0, 3)}
                                />
                                <YAxis
                                    axisLine={false}
                                    tickLine={false}
                                    tick={{ fontSize: 12, fill: '#888' }}
                                    tickFormatter={(val: number) => `₹${val / 1000}k`}
                                />
                                <Tooltip
                                    cursor={{ fill: '#f3f4f6' }}
                                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                                />
                                <Bar
                                    dataKey="total_amount"
                                    fill="#F97316" // Orange for purchases
                                    radius={[4, 4, 0, 0]}
                                    barSize={40}
                                />
                            </BarChart>
                        </ResponsiveContainer>
                    </CardContent>
                </Card>

                {/* Detailed Table */}
                <Card className="border-none shadow-sm bg-white overflow-hidden">
                    <CardHeader>
                        <CardTitle className="text-base font-medium">Monthly Breakdown</CardTitle>
                    </CardHeader>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="text-xs text-gray-500 uppercase bg-gray-50 border-b">
                                <tr>
                                    <th className="px-6 py-3 font-medium">Month</th>
                                    <th className="px-6 py-3 font-medium text-right">Vouchers</th>
                                    <th className="px-6 py-3 font-medium text-right">Total Purchases</th>
                                    <th className="px-6 py-3 font-medium text-right">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {data.monthly_data.map((month) => (
                                    <tr key={month.month_num} className="hover:bg-gray-50 transition-colors group">
                                        <td className="px-6 py-4 font-medium text-gray-900">{month.month_name}</td>
                                        <td className="px-6 py-4 text-right text-gray-600">{month.voucher_count}</td>
                                        <td className="px-6 py-4 text-right font-medium text-gray-900">
                                            ₹{month.total_amount.toLocaleString('en-IN')}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <button className="text-blue-600 hover:text-blue-800 text-xs font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                                                View Details →
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </Card>
            </main>
        </div>
    );
}
