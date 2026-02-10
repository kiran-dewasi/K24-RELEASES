"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Scale } from "lucide-react";
import Link from "next/link";

interface LedgerItem {
    name: string;
    amount: number;
    group: string;
}

interface BalanceSheetData {
    assets: LedgerItem[];
    liabilities: LedgerItem[];
    total_assets: number;
    total_liabilities: number;
    net_difference: number;
}

export default function BalanceSheetPage() {
    const [data, setData] = useState<BalanceSheetData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch("http://127.0.0.1:8000/reports/balance-sheet", {
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
                            <h1 className="text-xl font-semibold tracking-tight">Balance Sheet</h1>
                            <p className="text-xs text-gray-500">As of {new Date().toLocaleDateString()}</p>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <button className="px-3 py-1.5 text-sm font-medium bg-black text-white rounded-md hover:bg-gray-800 transition-colors">
                            Export PDF
                        </button>
                    </div>
                </div>
            </header>

            <main className="max-w-6xl mx-auto px-6 py-8">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {/* Liabilities Side */}
                    <Card className="border-none shadow-sm bg-white">
                        <CardHeader className="border-b border-gray-100 pb-4">
                            <CardTitle className="text-lg font-medium flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-red-500"></span>
                                Liabilities
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-0">
                            <div className="divide-y divide-gray-50">
                                {data.liabilities.map((item, idx) => (
                                    <div key={idx} className="flex justify-between items-center px-6 py-3 hover:bg-gray-50 transition-colors">
                                        <div>
                                            <p className="text-sm font-medium text-gray-900">{item.name}</p>
                                            <p className="text-xs text-gray-500">{item.group || 'Other Liabilities'}</p>
                                        </div>
                                        <span className="text-sm font-medium">₹{item.amount.toLocaleString('en-IN')}</span>
                                    </div>
                                ))}
                            </div>
                            <div className="bg-gray-50 px-6 py-4 border-t border-gray-100 flex justify-between items-center mt-4">
                                <span className="font-semibold text-gray-900">Total Liabilities</span>
                                <span className="font-bold text-lg">₹{data.total_liabilities.toLocaleString('en-IN')}</span>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Assets Side */}
                    <Card className="border-none shadow-sm bg-white">
                        <CardHeader className="border-b border-gray-100 pb-4">
                            <CardTitle className="text-lg font-medium flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-green-500"></span>
                                Assets
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-0">
                            <div className="divide-y divide-gray-50">
                                {data.assets.map((item, idx) => (
                                    <div key={idx} className="flex justify-between items-center px-6 py-3 hover:bg-gray-50 transition-colors">
                                        <div>
                                            <p className="text-sm font-medium text-gray-900">{item.name}</p>
                                            <p className="text-xs text-gray-500">{item.group || 'Other Assets'}</p>
                                        </div>
                                        <span className="text-sm font-medium">₹{item.amount.toLocaleString('en-IN')}</span>
                                    </div>
                                ))}
                            </div>
                            <div className="bg-gray-50 px-6 py-4 border-t border-gray-100 flex justify-between items-center mt-4">
                                <span className="font-semibold text-gray-900">Total Assets</span>
                                <span className="font-bold text-lg">₹{data.total_assets.toLocaleString('en-IN')}</span>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Net Difference Alert */}
                {Math.abs(data.net_difference) > 1 && (
                    <div className="mt-8 p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex items-center gap-3 text-yellow-800">
                        <Scale className="h-5 w-5" />
                        <div>
                            <p className="font-medium">Books are not balanced!</p>
                            <p className="text-sm">Difference of ₹{data.net_difference.toLocaleString('en-IN')} detected. Please run Tally Sync.</p>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}
