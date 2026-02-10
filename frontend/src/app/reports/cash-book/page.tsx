"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Wallet, RefreshCw } from "lucide-react";
import Link from "next/link";
import MagicInput from "@/components/MagicInput";

interface CashBookData {
    ledger_name: string;
    current_balance: number;
    last_synced: string;
}

export default function CashBookPage() {
    const [data, setData] = useState<CashBookData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch("http://127.0.0.1:8000/reports/cash-book", {
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
                            <h1 className="text-xl font-semibold tracking-tight">Cash Book</h1>
                            <p className="text-xs text-gray-500">Ledger: {data.ledger_name}</p>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <button className="px-3 py-1.5 text-sm font-medium bg-black text-white rounded-md hover:bg-gray-800 transition-colors flex items-center gap-2">
                            <RefreshCw className="h-3 w-3" /> Sync Now
                        </button>
                    </div>
                </div>
            </header>

            <main className="max-w-6xl mx-auto px-6 py-8 space-y-8">
                {/* Main Balance Card */}
                <Card className="border-none shadow-sm bg-gradient-to-br from-gray-900 to-gray-800 text-white">
                    <CardContent className="p-8 flex flex-col items-center justify-center text-center">
                        <div className="p-3 bg-white/10 rounded-full mb-4">
                            <Wallet className="h-8 w-8 text-white" />
                        </div>
                        <p className="text-sm font-medium text-gray-300 mb-1">Current Cash-in-Hand</p>
                        <div className="text-5xl font-bold tracking-tight">
                            ₹{(data.current_balance || 0).toLocaleString('en-IN')}
                        </div>
                        <p className="text-xs text-gray-400 mt-4">
                            Last Synced: {data.last_synced ? new Date(data.last_synced).toLocaleString() : 'Never'}
                        </p>
                    </CardContent>
                </Card>

                {/* Recent Transactions (Placeholder for now as backend doesn't return them yet) */}
                <Card className="border-none shadow-sm bg-white">
                    <CardHeader>
                        <CardTitle className="text-base font-medium">Recent Cash Transactions</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-center py-12 text-gray-500 text-sm">
                            <p>Detailed transaction view coming soon.</p>
                            <p className="text-xs mt-1">Use Daybook for full transaction history.</p>
                        </div>
                    </CardContent>
                </Card>

                {/* AI Assistant for this Page */}
                <div className="fixed bottom-6 right-6 w-full max-w-md z-50">
                    <MagicInput
                        isFullPage={false}
                        theme="light"
                        allowEmbedded={true}
                        pageContext={{
                            page: "cash-book",
                            ledger: data.ledger_name,
                            balance: data.current_balance
                        }}
                    />
                </div>
            </main>
        </div>
    );
}
