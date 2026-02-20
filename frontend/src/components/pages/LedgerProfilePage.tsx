"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-config";
import {
    ArrowLeft,
    Mail,
    Phone,
    MessageCircle,
    Edit,
    History,
    FileText,
    Calendar,
    Package,
    Loader2
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { formatDateForDisplay } from "@/lib/date-utils";
import { LedgerOverviewTab } from "@/components/ledger/LedgerOverviewTab";
import { LedgerTransactionsTab } from "@/components/ledger/LedgerTransactionsTab";
import { LedgerItemsTab } from "@/components/ledger/LedgerItemsTab";

interface LedgerDetails {
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
    financials?: {
        total_sales: number;
        total_purchases: number;
        customer_since: string;
        monthly_trend: Array<{ month: string, amount: number }>;
    };
}


function LedgerProfileContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const ledger_id = searchParams.get('id') || '';

    const [ledger, setLedger] = useState<LedgerDetails | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (ledger_id && ledger_id !== 'default') {
            fetchLedgerData();
        }
    }, [ledger_id]);

    const fetchLedgerData = async () => {
        setLoading(true);
        try {
            // Fetch Details
            const res = await apiClient(`/api/ledgers/${ledger_id}`);
            if (res.ok) {
                const data = await res.json();
                setLedger(data);
            }
        } catch (error) {
            console.error("Failed to fetch ledger details", error);
        } finally {
            setLoading(false);
        }
    };

    if (!ledger_id || ledger_id === 'default') {
        return <div className="p-8 text-center">Select a ledger to view details.</div>;
    }

    if (loading) {
        return <div className="p-8 text-center animate-pulse">Loading Ledger Profile...</div>;
    }

    if (!ledger) {
        return <div className="p-8 text-center text-muted-foreground">Ledger not found.</div>;
    }

    const formatCurrency = (amount: number) => {
        return Math.abs(amount).toLocaleString('en-IN', {
            style: 'currency',
            currency: 'INR'
        });
    };

    const isPositive = ledger.closing_balance >= 0;
    const balType = ledger.closing_balance >= 0 ? "Dr" : "Cr";
    const balanceColor = balType === "Dr" ? "text-emerald-600" : "text-rose-600";

    return (
        <div className="space-y-6 pb-24 max-w-[1600px] mx-auto p-4 md:p-6">

            {/* 1. Header Section (Sticky) */}
            <div className="sticky top-0 z-10 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-b pb-4 pt-2 -mx-4 px-4 md:-mx-6 md:px-6">
                <div className="flex flex-col gap-4">
                    {/* Top Row: Back + Title + Actions */}
                    <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                            <Button variant="ghost" size="icon" onClick={() => router.back()}>
                                <ArrowLeft className="h-4 w-4" />
                            </Button>
                            <div>
                                <h1 className="text-2xl font-bold tracking-tight">{ledger.name}</h1>
                                <div className="flex items-center gap-2 mt-1">
                                    <Badge variant="outline" className="text-muted-foreground">
                                        {ledger.group}
                                    </Badge>
                                    {ledger.gstin && (
                                        <Badge variant="secondary" className="font-mono text-xs">
                                            GSTIN: {ledger.gstin}
                                        </Badge>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Desktop Actions */}
                        <div className="hidden md:flex items-center gap-2">
                            <Button variant="outline" size="sm" className="gap-2">
                                <Mail className="h-4 w-4" /> Email
                            </Button>
                            <Button variant="outline" size="sm" className="gap-2">
                                <Phone className="h-4 w-4" /> Call
                            </Button>
                            <Button variant="outline" size="sm" className="gap-2 text-green-600 hover:text-green-700 hover:bg-green-50">
                                <MessageCircle className="h-4 w-4" /> WhatsApp
                            </Button>
                            <Button variant="default" size="sm" className="gap-2">
                                <Edit className="h-4 w-4" /> Edit
                            </Button>
                        </div>
                    </div>

                    {/* Balance Row (Mobile Optimized) */}
                    <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 bg-muted/30 p-4 rounded-lg border">
                        <div>
                            <p className="text-sm text-muted-foreground font-medium uppercase tracking-wider">Current Balance</p>
                            <div className={`text-3xl font-bold ${balanceColor} flex items-baseline gap-1`}>
                                {formatCurrency(Math.abs(ledger.closing_balance))}
                                <span className="text-lg font-medium text-muted-foreground">{balType}</span>
                            </div>
                        </div>

                        {/* Quick Stats */}
                        <div className="flex gap-8 text-sm">
                            <div>
                                <p className="text-muted-foreground">Last Transaction</p>
                                <p className="font-medium">
                                    {ledger.stats.last_transaction_date
                                        ? formatDateForDisplay(new Date(ledger.stats.last_transaction_date))
                                        : "N/A"
                                    }
                                </p>
                            </div>
                            <div>
                                <p className="text-muted-foreground">Total Txns</p>
                                <p className="font-medium">{ledger.stats.transaction_count}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* 2. Tab Navigation */}
            <Tabs defaultValue="transactions" className="w-full">
                <TabsList className="w-full justify-start overflow-x-auto h-auto p-1 gap-1">
                    <TabsTrigger value="overview" className="gap-2"><FileText className="h-4 w-4" /> Overview</TabsTrigger>
                    <TabsTrigger value="transactions" className="gap-2"><History className="h-4 w-4" /> Transactions</TabsTrigger>
                    <TabsTrigger value="items" className="gap-2"><Package className="h-4 w-4" /> Items</TabsTrigger>
                    <TabsTrigger value="aging" className="gap-2"><Calendar className="h-4 w-4" /> Aging Analysis</TabsTrigger>
                </TabsList>

                <div className="mt-6">
                    {/* Transactions Tab */}
                    <TabsContent value="transactions" className="space-y-4">
                        <LedgerTransactionsTab ledgerId={ledger.id} />
                    </TabsContent>

                    {/* Items Tab */}
                    <TabsContent value="items" className="space-y-4">
                        <LedgerItemsTab ledgerId={ledger.id} />
                    </TabsContent>

                    {/* Other Tabs Placeholders */}
                    <TabsContent value="overview">
                        <LedgerOverviewTab ledger={ledger} />
                    </TabsContent>
                    <TabsContent value="aging">
                        <Card>
                            <CardContent className="p-8 text-center text-muted-foreground">
                                Aging Analysis Chart (0-30, 30-60, 60-90 days) coming soon.
                            </CardContent>
                        </Card>
                    </TabsContent>
                </div>
            </Tabs>

        </div>
    );
}

export default function LedgerProfilePage() {
    return (
        <Suspense fallback={<div className="flex justify-center p-8"><Loader2 className="animate-spin" /></div>}>
            <LedgerProfileContent />
        </Suspense>
    );
}
