"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-config";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowLeft, Mail, Phone, MapPin, Building, ArrowUpRight, ArrowDownLeft, FileText, Download, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

interface LedgerProfile {
    id: number;
    name: string;
    group: string;
    closing_balance: number;
    email?: string;
    phone?: string;
    gstin?: string;
    address?: string;
    pan?: string;
    state_code?: string;
    stats: {
        transaction_count: number;
        last_transaction_date?: string;
    };
    financials: {
        total_sales: number;
        total_purchases: number;
        customer_since?: string;
        monthly_trend: Array<{ month: string, amount: number }>;
    };
}

interface Transaction {
    date: string;
    voucher_number: string;
    voucher_type: string;
    amount: number;
    narration: string;
    guid: string;
}




function PartyProfileContent() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const id = searchParams.get('id') || '';

    const [profile, setProfile] = useState<LedgerProfile | null>(null);
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (id && id !== 'default') {
            fetchProfile();
        }
    }, [id]);

    const fetchProfile = async () => {
        setLoading(true);
        try {
            // Fetch Profile
            const res = await apiClient(`/api/ledgers/${id}`);
            if (res.ok) {
                const data = await res.json();
                setProfile(data);
            }

            // Fetch Recent Transactions
            const txnsRes = await apiClient(`/api/ledgers/${id}/transactions?limit=20`);
            if (txnsRes.ok) {
                const data = await txnsRes.json();
                setTransactions(data.transactions || []);
            }

        } catch (error) {
            console.error("Failed to fetch profile", error);
        } finally {
            setLoading(false);
        }
    };

    const handleExport = () => {
        if (!profile) return;
        // Build CSV from transactions
        const rows = [
            ['Date', 'Voucher No', 'Type', 'Amount', 'Narration'],
            ...transactions.map(t => [
                new Date(t.date).toLocaleDateString('en-IN'),
                t.voucher_number,
                t.voucher_type,
                t.amount.toFixed(2),
                t.narration || ''
            ])
        ];
        const csv = rows.map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${profile.name.replace(/[^a-z0-9]/gi, '_')}_transactions.csv`;
        a.click();
        URL.revokeObjectURL(url);
    };

    if (id === 'default') {
        return <div className="p-8 text-center text-muted-foreground">Select a party to view profile.</div>;
    }

    if (loading) {
        return <div className="p-8 text-center animate-pulse">Loading profile...</div>;
    }

    if (!profile) {
        return (
            <div className="p-12 text-center text-muted-foreground">
                <p>Profile not found.</p>
                <Button variant="link" onClick={() => router.back()}>Go Back</Button>
            </div>
        );
    }

    return (
        <div className="max-w-[1600px] mx-auto pb-24 space-y-6">
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" onClick={() => router.back()}>
                    <ArrowLeft className="h-4 w-4" />
                </Button>
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">{profile.name}</h1>
                    <div className="flex items-center gap-2 text-muted-foreground mt-1 text-sm">
                        <Badge variant="outline">{profile.group}</Badge>
                        {profile.gstin && <span>• GSTIN: {profile.gstin}</span>}
                    </div>
                </div>
                <div className="ml-auto flex gap-2">
                    <Button
                        variant="default"
                        className="gap-2 bg-blue-600 hover:bg-blue-700"
                        onClick={() => router.push(`/customers?id=${id}`)}
                    >
                        <ArrowUpRight className="h-4 w-4" /> View 360° Profile
                    </Button>
                    <Button
                        variant="outline"
                        className="gap-2"
                        onClick={() => handleExport()}
                    >
                        <Download className="h-4 w-4" /> Export
                    </Button>
                    <Button
                        className="gap-2"
                        onClick={() => router.push(`/vouchers/new/sales?party=${encodeURIComponent(profile?.name || '')}`)}
                    >
                        <FileText className="h-4 w-4" /> Create Invoice
                    </Button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Left Column: Basic Info & Contact */}
                <div className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Contact Details</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {profile.email && (
                                <div className="flex items-center gap-3">
                                    <Mail className="h-4 w-4 text-muted-foreground" />
                                    <a href={`mailto:${profile.email}`} className="text-sm hover:underline">{profile.email}</a>
                                </div>
                            )}
                            {profile.phone && (
                                <div className="flex items-center gap-3">
                                    <Phone className="h-4 w-4 text-muted-foreground" />
                                    <a href={`tel:${profile.phone}`} className="text-sm hover:underline">{profile.phone}</a>
                                </div>
                            )}
                            {profile.address && (
                                <div className="flex items-start gap-3">
                                    <MapPin className="h-4 w-4 text-muted-foreground mt-1" />
                                    <span className="text-sm whitespace-pre-line">{profile.address}</span>
                                </div>
                            )}
                            {!profile.email && !profile.phone && !profile.address && (
                                <p className="text-sm text-muted-foreground italic">No contact info available.</p>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Overview</CardTitle>
                        </CardHeader>
                        <CardContent className="grid grid-cols-2 gap-4">
                            <div>
                                <p className="text-xs text-muted-foreground uppercase">Closing Balance</p>
                                <p className={`text-lg font-bold ${profile.closing_balance < 0 ? 'text-red-600' : 'text-green-600'}`}>
                                    ₹{Math.abs(profile.closing_balance).toLocaleString('en-IN')} {profile.closing_balance < 0 ? 'Dr' : 'Cr'}
                                </p>
                            </div>
                            <div>
                                <p className="text-xs text-muted-foreground uppercase">Total Txns</p>
                                <p className="text-lg font-bold">{profile.stats.transaction_count}</p>
                            </div>
                            <div>
                                <p className="text-xs text-muted-foreground uppercase">Total Sales</p>
                                <p className="text-sm font-medium">₹{(profile.financials?.total_sales || 0).toLocaleString('en-IN')}</p>
                            </div>
                            <div>
                                <p className="text-xs text-muted-foreground uppercase">Total Purchases</p>
                                <p className="text-sm font-medium">₹{(profile.financials?.total_purchases || 0).toLocaleString('en-IN')}</p>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Right Column: Transactions & Analytics */}
                <div className="md:col-span-2 space-y-6">
                    <Tabs defaultValue="transactions">
                        <TabsList>
                            <TabsTrigger value="transactions">Transactions</TabsTrigger>
                            <TabsTrigger value="analytics" disabled>Analytics (Coming Soon)</TabsTrigger>
                        </TabsList>

                        <TabsContent value="transactions" className="space-y-4">
                            <Card>
                                <CardHeader className="pb-3">
                                    <CardTitle className="text-lg">Recent History</CardTitle>
                                    <CardDescription>Last 20 transactions for this party</CardDescription>
                                </CardHeader>
                                <CardContent className="p-0">
                                    <div className="rounded-md border border-t-0 border-x-0 border-b-0">
                                        <table className="w-full text-sm">
                                            <thead>
                                                <tr className="border-b bg-muted/40">
                                                    <th className="h-10 px-4 text-left font-medium">Date</th>
                                                    <th className="h-10 px-4 text-left font-medium">Voucher No</th>
                                                    <th className="h-10 px-4 text-left font-medium">Type</th>
                                                    <th className="h-10 px-4 text-right font-medium">Amount</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {transactions.map((txn, i) => (
                                                    <tr key={i} className="border-b hover:bg-muted/50 transition-colors">
                                                        <td className="p-4 align-middle">
                                                            {new Date(txn.date).toLocaleDateString()}
                                                        </td>
                                                        <td className="p-4 align-middle font-mono">
                                                            {txn.voucher_number}
                                                        </td>
                                                        <td className="p-4 align-middle">
                                                            <Badge variant="outline" className="font-normal">
                                                                {txn.voucher_type}
                                                            </Badge>
                                                        </td>
                                                        <td className="p-4 align-middle text-right font-mono">
                                                            ₹{txn.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                                                        </td>
                                                    </tr>
                                                ))}
                                                {transactions.length === 0 && (
                                                    <tr>
                                                        <td colSpan={4} className="p-8 text-center text-muted-foreground">
                                                            No transactions found.
                                                        </td>
                                                    </tr>
                                                )}
                                            </tbody>
                                        </table>
                                    </div>
                                </CardContent>
                            </Card>
                        </TabsContent>
                    </Tabs>
                </div>
            </div>
        </div>
    );
}

export default function PartyProfilePage() {
    return (
        <Suspense fallback={
            <div className="flex bg-slate-50 min-h-screen items-center justify-center">
                <Loader2 className="animate-spin h-8 w-8 text-muted-foreground" />
            </div>
        }>
            <PartyProfileContent />
        </Suspense>
    );
}
