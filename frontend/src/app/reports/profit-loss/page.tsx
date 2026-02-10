"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, TrendingUp, TrendingDown } from "lucide-react";
import Link from "next/link";

interface PLData {
    income: Record<string, number>;
    expenses: Record<string, number>;
    total_income: number;
    total_expenses: number;
    net_profit: number;
}

export default function ProfitLossPage() {
    const [data, setData] = useState<PLData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch("http://127.0.0.1:8000/reports/profit-loss", {
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

    const isProfit = data.net_profit >= 0;

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
                            <h1 className="text-xl font-semibold tracking-tight">Profit & Loss A/c</h1>
                            <p className="text-xs text-gray-500">For the year ended {new Date().getFullYear()}</p>
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
                {/* Net Profit Hero Card */}
                <Card className={`border-none shadow-sm ${isProfit ? 'bg-green-50' : 'bg-red-50'}`}>
                    <CardContent className="p-8 flex flex-col items-center justify-center text-center">
                        <div className={`p-3 rounded-full mb-4 ${isProfit ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'}`}>
                            {isProfit ? <TrendingUp className="h-8 w-8" /> : <TrendingDown className="h-8 w-8" />}
                        </div>
                        <p className="text-sm font-medium text-gray-500 mb-1">{isProfit ? 'Net Profit' : 'Net Loss'}</p>
                        <div className={`text-5xl font-bold tracking-tight ${isProfit ? 'text-green-700' : 'text-red-700'}`}>
                            ₹{Math.abs(data.net_profit).toLocaleString('en-IN')}
                        </div>
                    </CardContent>
                </Card>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {/* Expenses Side */}
                    <Card className="border-none shadow-sm bg-white">
                        <CardHeader className="border-b border-gray-100 pb-4">
                            <CardTitle className="text-lg font-medium">Expenses</CardTitle>
                        </CardHeader>
                        <CardContent className="p-0">
                            <div className="divide-y divide-gray-50">
                                {Object.entries(data.expenses).map(([name, amount], idx) => (
                                    <div key={idx} className="flex justify-between items-center px-6 py-3 hover:bg-gray-50 transition-colors">
                                        <span className="text-sm font-medium text-gray-900">{name}</span>
                                        <span className="text-sm font-medium">₹{amount.toLocaleString('en-IN')}</span>
                                    </div>
                                ))}
                            </div>
                            <div className="bg-gray-50 px-6 py-4 border-t border-gray-100 flex justify-between items-center mt-4">
                                <span className="font-semibold text-gray-900">Total Expenses</span>
                                <span className="font-bold text-lg">₹{data.total_expenses.toLocaleString('en-IN')}</span>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Income Side */}
                    <Card className="border-none shadow-sm bg-white">
                        <CardHeader className="border-b border-gray-100 pb-4">
                            <CardTitle className="text-lg font-medium">Income</CardTitle>
                        </CardHeader>
                        <CardContent className="p-0">
                            <div className="divide-y divide-gray-50">
                                {Object.entries(data.income).map(([name, amount], idx) => (
                                    <div key={idx} className="flex justify-between items-center px-6 py-3 hover:bg-gray-50 transition-colors">
                                        <span className="text-sm font-medium text-gray-900">{name}</span>
                                        <span className="text-sm font-medium">₹{amount.toLocaleString('en-IN')}</span>
                                    </div>
                                ))}
                            </div>
                            <div className="bg-gray-50 px-6 py-4 border-t border-gray-100 flex justify-between items-center mt-4">
                                <span className="font-semibold text-gray-900">Total Income</span>
                                <span className="font-bold text-lg">₹{data.total_income.toLocaleString('en-IN')}</span>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </main>
        </div>
    );
}
