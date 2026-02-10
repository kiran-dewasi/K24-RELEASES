"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
    MapPin,
    Phone,
    Mail,
    CreditCard,
    FileText,
    ShieldCheck,
    CalendarClock,
    TrendingUp,
    FilePlus,
    Receipt,
    Banknote,
    MessageSquareText
} from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { formatDateForDisplay } from "@/lib/date-utils";

interface LedgerOverviewProps {
    ledger: any; // Using any for flexibility based on new backend response, or define precise interface
}

export function LedgerOverviewTab({ ledger }: LedgerOverviewProps) {

    // Safety check for financials
    const financials = ledger.financials || {
        total_sales: 0,
        total_purchases: 0,
        customer_since: null,
        monthly_trend: []
    };

    const formatCurrency = (amount: number) => {
        return Math.abs(amount).toLocaleString('en-IN', {
            style: 'currency',
            currency: 'INR',
            maximumFractionDigits: 0
        });
    };

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

            {/* Left Column: Contact & Relationships (Span 1) */}
            <div className="space-y-6">

                {/* 1. Contact Info Card */}
                <Card>
                    <CardHeader className="pb-3 border-b bg-muted/20">
                        <div className="flex justify-between items-center">
                            <CardTitle className="text-base font-semibold">Contact Details</CardTitle>
                            <Button variant="ghost" size="sm" className="h-8 text-xs text-primary">Edit</Button>
                        </div>
                    </CardHeader>
                    <CardContent className="pt-4 space-y-4">
                        <div className="flex gap-3 items-start">
                            <MapPin className="h-4 w-4 text-muted-foreground mt-1 min-w-4" />
                            <div className="text-sm">
                                <p className="text-foreground">{ledger.address || "No address provided"}</p>
                                {ledger.state_code && <p className="text-muted-foreground text-xs mt-1">State Code: {ledger.state_code}</p>}
                            </div>
                        </div>

                        <div className="flex gap-3 items-center">
                            <Phone className="h-4 w-4 text-muted-foreground min-w-4" />
                            <p className="text-sm">{ledger.phone || "No phone linked"}</p>
                        </div>

                        <div className="flex gap-3 items-center">
                            <Mail className="h-4 w-4 text-muted-foreground min-w-4" />
                            <p className="text-sm text-blue-600 hover:underline cursor-pointer">{ledger.email || "No email"}</p>
                        </div>

                        <Separator />

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <p className="text-xs text-muted-foreground mb-1">GSTIN</p>
                                <div className="flex items-center gap-1">
                                    <ShieldCheck className="h-3 w-3 text-green-600" />
                                    <span className="text-sm font-mono">{ledger.gstin || "N/A"}</span>
                                </div>
                            </div>
                            <div>
                                <p className="text-xs text-muted-foreground mb-1">PAN</p>
                                <span className="text-sm font-mono">{ledger.pan || "N/A"}</span>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* 3. Relationship Metrics */}
                <Card>
                    <CardHeader className="pb-3 border-b bg-muted/20">
                        <CardTitle className="text-base font-semibold">Business Relationship</CardTitle>
                    </CardHeader>
                    <CardContent className="pt-4 space-y-4">
                        <div className="flex justify-between items-center">
                            <div className="flex items-center gap-2">
                                <CalendarClock className="h-4 w-4 text-muted-foreground" />
                                <span className="text-sm text-muted-foreground">Customer Since</span>
                            </div>
                            <span className="text-sm font-medium">
                                {financials.customer_since
                                    ? formatDateForDisplay(new Date(financials.customer_since))
                                    : "N/A"
                                }
                            </span>
                        </div>

                        <div className="flex justify-between items-center">
                            <div className="flex items-center gap-2">
                                <FileText className="h-4 w-4 text-muted-foreground" />
                                <span className="text-sm text-muted-foreground">Total Transactions</span>
                            </div>
                            <span className="text-sm font-medium">{ledger.stats.transaction_count}</span>
                        </div>

                        <div className="flex justify-between items-center">
                            <div className="flex items-center gap-2">
                                <CreditCard className="h-4 w-4 text-muted-foreground" />
                                <span className="text-sm text-muted-foreground">Preferred Method</span>
                            </div>
                            <Badge variant="secondary" className="text-xs font-normal">Bank Transfer</Badge>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Right Column: Financials (Span 2) */}
            <div className="md:col-span-2 space-y-6">

                {/* 2. Financial Summary Card */}
                <Card className="overflow-hidden">
                    <CardHeader className="pb-4 bg-gradient-to-r from-muted/50 to-background border-b">
                        <div className="flex justify-between items-center">
                            <div className="space-y-1">
                                <CardTitle className="text-lg">Financial Overview</CardTitle>
                                <CardDescription>Key financial performance metrics for this fiscal year</CardDescription>
                            </div>
                            <div className="text-right">
                                <p className="text-xs text-muted-foreground uppercase font-bold tracking-wider">Outstanding Balance</p>
                                <p className={`text-2xl font-bold ${ledger.closing_balance >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                                    {formatCurrency(ledger.closing_balance)}
                                    <span className="text-sm text-muted-foreground ml-1 font-normal">
                                        {ledger.closing_balance >= 0 ? "Dr" : "Cr"}
                                    </span>
                                </p>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent className="p-6">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8">
                            <div className="space-y-1">
                                <p className="text-xs text-muted-foreground">Total Sales (YTD)</p>
                                <p className="text-xl font-semibold">{formatCurrency(financials.total_sales)}</p>
                            </div>
                            <div className="space-y-1">
                                <p className="text-xs text-muted-foreground">Total Purchases (YTD)</p>
                                <p className="text-xl font-semibold">{formatCurrency(financials.total_purchases)}</p>
                            </div>
                            <div className="space-y-1">
                                <p className="text-xs text-muted-foreground">Avg Payment Days</p>
                                <p className="text-xl font-semibold">12 <span className="text-sm font-normal text-muted-foreground">days</span></p>
                            </div>
                            <div className="space-y-1">
                                <p className="text-xs text-muted-foreground">Credit Limit</p>
                                <p className="text-xl font-semibold text-muted-foreground">₹2,00,000</p>
                            </div>
                        </div>

                        {/* Chart Area */}
                        <div className="h-[200px] w-full">
                            <p className="text-xs font-medium text-muted-foreground mb-4 flex items-center gap-2">
                                <TrendingUp className="h-3 w-3" /> Monthly Transaction Volume
                            </p>
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={financials.monthly_trend}>
                                    <XAxis
                                        dataKey="month"
                                        tick={{ fontSize: 12 }}
                                        axisLine={false}
                                        tickLine={false}
                                    />
                                    <YAxis hide />
                                    <Tooltip
                                        formatter={(val: any) => formatCurrency(Number(val) || 0)}
                                        contentStyle={{ borderRadius: '8px', fontSize: '12px' }}
                                    />
                                    <Bar
                                        dataKey="amount"
                                        fill="#3b82f6"
                                        radius={[4, 4, 0, 0]}
                                        barSize={40}
                                    />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </CardContent>
                </Card>

                {/* 4. Quick Actions */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <Button className="h-auto py-4 flex flex-col gap-2 border bg-card hover:bg-accent hover:text-accent-foreground text-foreground shadow-sm" variant="outline">
                        <FilePlus className="h-6 w-6 text-blue-600" />
                        <span className="text-xs font-medium">New Invoice</span>
                    </Button>
                    <Button className="h-auto py-4 flex flex-col gap-2 border bg-card hover:bg-accent hover:text-accent-foreground text-foreground shadow-sm" variant="outline">
                        <Banknote className="h-6 w-6 text-green-600" />
                        <span className="text-xs font-medium">Record Payment</span>
                    </Button>
                    <Button className="h-auto py-4 flex flex-col gap-2 border bg-card hover:bg-accent hover:text-accent-foreground text-foreground shadow-sm" variant="outline">
                        <Receipt className="h-6 w-6 text-orange-600" />
                        <span className="text-xs font-medium">Statement</span>
                    </Button>
                    <Button className="h-auto py-4 flex flex-col gap-2 border bg-card hover:bg-accent hover:text-accent-foreground text-foreground shadow-sm" variant="outline">
                        <MessageSquareText className="h-6 w-6 text-purple-600" />
                        <span className="text-xs font-medium">Add Note</span>
                    </Button>
                </div>

            </div>
        </div>
    );
}
