'use client';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
    ArrowLeft, Phone, Mail, MapPin, FileText, Download,
    TrendingUp, TrendingDown, AlertTriangle, CheckCircle,
    Clock, CreditCard, Package, BarChart3, RefreshCw, Loader2
} from 'lucide-react';

// --- Types ---
interface Customer360Data {
    customer: {
        id: number;
        name: string;
        alias?: string;
        group?: string;
        ledger_type?: string;
        gstin?: string;
        pan?: string;
        phone?: string;
        email?: string;
        address?: string;
        city?: string;
        state?: string;
        pincode?: string;
        contact_person?: string;
        opening_balance?: number;
        closing_balance?: number;
        credit_limit?: number;
        credit_days?: number;
        created_at?: string;
    };
    summary: {
        transaction_count: number;
        total_sales: number;
        total_receipts: number;
        total_purchases: number;
        total_payments: number;
        first_transaction_date?: string;
        last_transaction_date?: string;
        outstanding_total: number;
        overdue_total: number;
        outstanding_count: number;
        overdue_count: number;
        credit_days_avg: number;
        payment_promptness: number;
        current_balance: number;
        credit_limit?: number;
        credit_utilized_pct: number;
    };
    outstanding_bills: Array<{
        bill_name: string;
        amount: number;
        pending_amount: number;
        due_date?: string;
        overdue_days: number;
        is_overdue: boolean;
        aging_bucket: string;
    }>;
    recent_payments: Array<{
        id: number;
        date: string;
        voucher_number: string;
        amount: number;
        narration?: string;
    }>;
    recent_transactions: Array<{
        id: number;
        date: string;
        voucher_number: string;
        voucher_type: string;
        amount: number;
        narration?: string;
        status?: string;
    }>;
    top_items: Array<{
        item_name: string;
        total_quantity: number;
        total_value: number;
        transaction_count: number;
        avg_rate: number;
        last_date?: string;
    }>;
    monthly_trend: Array<{
        month: string;
        label: string;
        sales: number;
        receipts: number;
        purchases: number;
        payments: number;
        net: number;
    }>;
    insights: {
        avg_credit_days: number;
        payment_score: number;
        health_score: number;
        risk_level: string;
        customer_tier: string;
        trend: string;
        recommendations: string[];
    };
    health_score: number;
}

// --- Helper Components ---
function MetricCard({
    title,
    value,
    subtitle,
    icon,
    trend,
    color = 'blue'
}: {
    title: string;
    value: string | number;
    subtitle?: string;
    icon?: React.ReactNode;
    trend?: 'up' | 'down' | 'neutral';
    color?: 'blue' | 'green' | 'red' | 'orange' | 'purple';
}) {
    const colorClasses = {
        blue: 'bg-blue-50 text-blue-700 border-blue-200',
        green: 'bg-green-50 text-green-700 border-green-200',
        red: 'bg-red-50 text-red-700 border-red-200',
        orange: 'bg-orange-50 text-orange-700 border-orange-200',
        purple: 'bg-purple-50 text-purple-700 border-purple-200',
    };

    return (
        <Card className={`border ${colorClasses[color]}`}>
            <CardContent className="p-4">
                <div className="flex items-start justify-between">
                    <div>
                        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{title}</p>
                        <p className="text-2xl font-bold mt-1">{value}</p>
                        {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
                    </div>
                    {icon && <div className="text-2xl">{icon}</div>}
                </div>
                {trend && (
                    <div className="mt-2 flex items-center text-xs">
                        {trend === 'up' && <TrendingUp className="h-3 w-3 text-green-500 mr-1" />}
                        {trend === 'down' && <TrendingDown className="h-3 w-3 text-red-500 mr-1" />}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

function HealthScoreRing({ score, size = 120 }: { score: number; size?: number }) {
    const radius = (size - 12) / 2;
    const circumference = 2 * Math.PI * radius;
    const progress = (score / 100) * circumference;

    const getColor = (score: number) => {
        if (score >= 80) return '#22c55e'; // green
        if (score >= 60) return '#f59e0b'; // orange
        return '#ef4444'; // red
    };

    return (
        <div className="relative" style={{ width: size, height: size }}>
            <svg width={size} height={size} className="transform -rotate-90">
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    fill="none"
                    stroke="#e5e7eb"
                    strokeWidth="8"
                />
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    fill="none"
                    stroke={getColor(score)}
                    strokeWidth="8"
                    strokeDasharray={circumference}
                    strokeDashoffset={circumference - progress}
                    strokeLinecap="round"
                    className="transition-all duration-1000 ease-out"
                />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold" style={{ color: getColor(score) }}>{score}</span>
                <span className="text-xs text-gray-500">Health</span>
            </div>
        </div>
    );
}

function AgingBadge({ bucket }: { bucket: string }) {
    const colors: Record<string, string> = {
        'current': 'bg-green-100 text-green-700',
        '1-30 days': 'bg-yellow-100 text-yellow-700',
        '31-60 days': 'bg-orange-100 text-orange-700',
        '61-90 days': 'bg-red-100 text-red-700',
        '90+ days': 'bg-red-200 text-red-800',
    };

    return (
        <Badge className={colors[bucket] || 'bg-gray-100 text-gray-700'}>
            {bucket}
        </Badge>
    );
}

function TierBadge({ tier }: { tier: string }) {
    const colors: Record<string, string> = {
        'platinum': 'bg-gradient-to-r from-gray-700 to-gray-900 text-white',
        'gold': 'bg-gradient-to-r from-yellow-400 to-yellow-600 text-white',
        'silver': 'bg-gradient-to-r from-gray-300 to-gray-500 text-white',
        'bronze': 'bg-gradient-to-r from-orange-400 to-orange-600 text-white',
    };

    return (
        <Badge className={`${colors[tier] || 'bg-gray-100'} px-3 py-1 text-sm font-semibold`}>
            {tier.charAt(0).toUpperCase() + tier.slice(1)}
        </Badge>
    );
}

// --- Main Component ---



function Customer360Content() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const id = searchParams.get('id') || '';

    const [data, setData] = useState<Customer360Data | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const token = localStorage.getItem('k24_token');
            const headers: Record<string, string> = { 'x-api-key': 'k24-secret-key-123' };
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const res = await fetch(`${API_URL}/api/customers/${id}/360`, { headers });

            if (!res.ok) {
                if (res.status === 404) {
                    setError('Customer not found');
                } else {
                    setError('Failed to load customer data');
                }
                return;
            }

            const data = await res.json();
            setData(data);
        } catch (err) {
            console.error('Error fetching customer 360:', err);
            setError('Failed to connect to server');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (id && id !== 'default') fetchData();
    }, [id]);

    const formatCurrency = (amount: number) => {
        return `₹${Math.abs(amount).toLocaleString('en-IN', { minimumFractionDigits: 0 })}`;
    };

    if (id === 'default') {
        return <div className="p-8 text-center text-muted-foreground">Select a customer to view 360 profile.</div>;
    }

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="mt-4 text-gray-500">Loading customer profile...</p>
                </div>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="flex h-screen items-center justify-center">
                <Card className="max-w-md w-full text-center p-8">
                    <AlertTriangle className="h-12 w-12 text-orange-500 mx-auto mb-4" />
                    <h2 className="text-xl font-bold mb-2">{error || 'Customer not found'}</h2>
                    <p className="text-gray-500 mb-6">Unable to load customer profile.</p>
                    <Button variant="outline" onClick={() => router.back()}>Go Back</Button>
                </Card>
            </div>
        );
    }

    const { customer, summary, outstanding_bills, recent_payments, recent_transactions, top_items, monthly_trend, insights } = data;

    return (
        <div className="min-h-screen bg-gray-50 pb-12">
            {/* Header */}
            <div className="bg-white border-b sticky top-0 z-10">
                <div className="max-w-7xl mx-auto px-6 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <Button variant="ghost" size="icon" onClick={() => router.back()}>
                                <ArrowLeft className="h-5 w-5" />
                            </Button>
                            <div>
                                <div className="flex items-center gap-3">
                                    <h1 className="text-2xl font-bold">{customer.name}</h1>
                                    <TierBadge tier={insights.customer_tier} />
                                    {insights.risk_level === 'high' && (
                                        <Badge variant="destructive" className="animate-pulse">High Risk</Badge>
                                    )}
                                </div>
                                <div className="flex items-center gap-4 text-sm text-gray-500 mt-1">
                                    <span>{customer.group}</span>
                                    {customer.gstin && <span>• GSTIN: {customer.gstin}</span>}
                                </div>
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            <Button variant="outline" size="sm" onClick={fetchData}>
                                <RefreshCw className="h-4 w-4 mr-2" />
                                Refresh
                            </Button>
                            <Button variant="outline" size="sm">
                                <Download className="h-4 w-4 mr-2" />
                                Export
                            </Button>
                            <Button size="sm" className="bg-blue-600 hover:bg-blue-700">
                                <FileText className="h-4 w-4 mr-2" />
                                Create Invoice
                            </Button>
                        </div>
                    </div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-6 py-6">
                {/* Top Row: Profile + Health Score + Key Metrics */}
                <div className="grid grid-cols-12 gap-6 mb-6">
                    {/* Contact Info Card */}
                    <Card className="col-span-4">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-lg">Contact Information</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                            {customer.phone && (
                                <div className="flex items-center gap-3">
                                    <Phone className="h-4 w-4 text-gray-400" />
                                    <a href={`tel:${customer.phone}`} className="text-sm hover:underline">{customer.phone}</a>
                                </div>
                            )}
                            {customer.email && (
                                <div className="flex items-center gap-3">
                                    <Mail className="h-4 w-4 text-gray-400" />
                                    <a href={`mailto:${customer.email}`} className="text-sm hover:underline">{customer.email}</a>
                                </div>
                            )}
                            {(customer.address || customer.city) && (
                                <div className="flex items-start gap-3">
                                    <MapPin className="h-4 w-4 text-gray-400 mt-0.5" />
                                    <span className="text-sm">
                                        {[customer.address, customer.city, customer.state, customer.pincode].filter(Boolean).join(', ')}
                                    </span>
                                </div>
                            )}
                            {customer.contact_person && (
                                <div className="text-sm text-gray-500">
                                    Contact: <span className="font-medium text-gray-700">{customer.contact_person}</span>
                                </div>
                            )}
                            {!customer.phone && !customer.email && !customer.address && (
                                <p className="text-sm text-gray-400 italic">No contact info available</p>
                            )}

                            {/* Credit Info */}
                            {(customer.credit_limit || customer.credit_days) && (
                                <div className="pt-3 border-t mt-4">
                                    <p className="text-xs font-medium text-gray-500 uppercase mb-2">Credit Terms</p>
                                    <div className="grid grid-cols-2 gap-2 text-sm">
                                        {customer.credit_limit && (
                                            <div>
                                                <span className="text-gray-500">Limit:</span>{' '}
                                                <span className="font-medium">{formatCurrency(customer.credit_limit)}</span>
                                            </div>
                                        )}
                                        {customer.credit_days && (
                                            <div>
                                                <span className="text-gray-500">Days:</span>{' '}
                                                <span className="font-medium">{customer.credit_days}</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* Health Score Card */}
                    <Card className="col-span-3">
                        <CardContent className="p-6 flex flex-col items-center justify-center h-full">
                            <HealthScoreRing score={data.health_score} size={140} />
                            <div className="mt-4 text-center">
                                <Badge className={
                                    insights.risk_level === 'low' ? 'bg-green-100 text-green-700' :
                                        insights.risk_level === 'medium' ? 'bg-orange-100 text-orange-700' :
                                            'bg-red-100 text-red-700'
                                }>
                                    {insights.risk_level.charAt(0).toUpperCase() + insights.risk_level.slice(1)} Risk
                                </Badge>
                                <div className="flex items-center justify-center gap-1 mt-2 text-sm text-gray-500">
                                    {insights.trend === 'growing' && <TrendingUp className="h-4 w-4 text-green-500" />}
                                    {insights.trend === 'declining' && <TrendingDown className="h-4 w-4 text-red-500" />}
                                    <span>{insights.trend.charAt(0).toUpperCase() + insights.trend.slice(1)} trend</span>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Key Metrics */}
                    <div className="col-span-5 grid grid-cols-2 gap-4">
                        <MetricCard
                            title="Current Balance"
                            value={formatCurrency(summary.current_balance)}
                            subtitle={summary.current_balance >= 0 ? 'Receivable' : 'Payable'}
                            icon={<CreditCard className="h-6 w-6" />}
                            color={summary.current_balance >= 0 ? 'green' : 'red'}
                        />
                        <MetricCard
                            title="Total Sales"
                            value={formatCurrency(summary.total_sales)}
                            subtitle="Last 12 months"
                            icon="💰"
                            color="blue"
                        />
                        <MetricCard
                            title="Transactions"
                            value={summary.transaction_count}
                            subtitle="Total transactions"
                            icon={<BarChart3 className="h-6 w-6" />}
                            color="purple"
                        />
                        <MetricCard
                            title="Payment Score"
                            value={`${summary.payment_promptness}%`}
                            subtitle={summary.payment_promptness >= 80 ? 'Excellent' : 'Needs attention'}
                            icon={summary.payment_promptness >= 80 ? <CheckCircle className="h-6 w-6" /> : <Clock className="h-6 w-6" />}
                            color={summary.payment_promptness >= 80 ? 'green' : 'orange'}
                        />
                    </div>
                </div>

                {/* Insights Banner */}
                {insights.recommendations.length > 0 && (
                    <Card className="mb-6 border-blue-200 bg-blue-50">
                        <CardContent className="p-4">
                            <div className="flex items-start gap-3">
                                <div className="p-2 bg-blue-100 rounded-full">
                                    <AlertTriangle className="h-5 w-5 text-blue-600" />
                                </div>
                                <div>
                                    <h3 className="font-semibold text-blue-800">Insights & Recommendations</h3>
                                    <ul className="mt-2 space-y-1">
                                        {insights.recommendations.map((rec, i) => (
                                            <li key={i} className="text-sm text-blue-700 flex items-center gap-2">
                                                <span className="w-1.5 h-1.5 bg-blue-500 rounded-full"></span>
                                                {rec}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Main Tabs */}
                <Tabs defaultValue="outstanding" className="space-y-6">
                    <TabsList className="bg-white border">
                        <TabsTrigger value="outstanding">
                            Outstanding ({outstanding_bills.length})
                        </TabsTrigger>
                        <TabsTrigger value="transactions">Transactions</TabsTrigger>
                        <TabsTrigger value="payments">Payments</TabsTrigger>
                        <TabsTrigger value="items">Top Items</TabsTrigger>
                        <TabsTrigger value="analytics">Analytics</TabsTrigger>
                    </TabsList>

                    {/* Outstanding Bills Tab */}
                    <TabsContent value="outstanding">
                        <Card>
                            <CardHeader>
                                <div className="flex justify-between items-center">
                                    <div>
                                        <CardTitle>Outstanding Bills</CardTitle>
                                        <CardDescription>
                                            {summary.overdue_count > 0
                                                ? `${summary.overdue_count} bills overdue (${formatCurrency(summary.overdue_total)})`
                                                : 'All bills current'
                                            }
                                        </CardDescription>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-2xl font-bold text-red-600">{formatCurrency(summary.outstanding_total)}</p>
                                        <p className="text-sm text-gray-500">Total Outstanding</p>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent>
                                {outstanding_bills.length > 0 ? (
                                    <table className="w-full">
                                        <thead>
                                            <tr className="border-b bg-gray-50">
                                                <th className="text-left py-3 px-4 text-sm font-medium">Bill #</th>
                                                <th className="text-left py-3 px-4 text-sm font-medium">Due Date</th>
                                                <th className="text-left py-3 px-4 text-sm font-medium">Aging</th>
                                                <th className="text-right py-3 px-4 text-sm font-medium">Amount</th>
                                                <th className="text-right py-3 px-4 text-sm font-medium">Pending</th>
                                                <th className="text-right py-3 px-4 text-sm font-medium">Overdue Days</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {outstanding_bills.map((bill, i) => (
                                                <tr key={i} className="border-b hover:bg-gray-50 transition-colors">
                                                    <td className="py-3 px-4 font-medium">{bill.bill_name}</td>
                                                    <td className="py-3 px-4 text-gray-600">{bill.due_date || '-'}</td>
                                                    <td className="py-3 px-4"><AgingBadge bucket={bill.aging_bucket} /></td>
                                                    <td className="py-3 px-4 text-right">{formatCurrency(bill.amount)}</td>
                                                    <td className="py-3 px-4 text-right font-semibold">{formatCurrency(bill.pending_amount)}</td>
                                                    <td className={`py-3 px-4 text-right ${bill.overdue_days > 0 ? 'text-red-600 font-medium' : 'text-gray-400'}`}>
                                                        {bill.overdue_days > 0 ? `${bill.overdue_days} days` : '-'}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                ) : (
                                    <div className="text-center py-12 text-gray-500">
                                        <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-500" />
                                        <p className="font-medium">No outstanding bills</p>
                                        <p className="text-sm">All invoices have been paid</p>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* Transactions Tab */}
                    <TabsContent value="transactions">
                        <Card>
                            <CardHeader>
                                <CardTitle>Recent Transactions</CardTitle>
                                <CardDescription>Last 20 transactions with this customer</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <table className="w-full">
                                    <thead>
                                        <tr className="border-b bg-gray-50">
                                            <th className="text-left py-3 px-4 text-sm font-medium">Date</th>
                                            <th className="text-left py-3 px-4 text-sm font-medium">Voucher #</th>
                                            <th className="text-left py-3 px-4 text-sm font-medium">Type</th>
                                            <th className="text-left py-3 px-4 text-sm font-medium">Narration</th>
                                            <th className="text-right py-3 px-4 text-sm font-medium">Amount</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {recent_transactions.map((txn, i) => (
                                            <tr key={i} className="border-b hover:bg-gray-50 transition-colors">
                                                <td className="py-3 px-4">{txn.date}</td>
                                                <td className="py-3 px-4 font-mono text-sm">{txn.voucher_number}</td>
                                                <td className="py-3 px-4">
                                                    <Badge variant="outline">{txn.voucher_type}</Badge>
                                                </td>
                                                <td className="py-3 px-4 text-gray-600 text-sm max-w-xs truncate">
                                                    {txn.narration || '-'}
                                                </td>
                                                <td className="py-3 px-4 text-right font-mono">
                                                    {formatCurrency(txn.amount)}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                                {recent_transactions.length === 0 && (
                                    <div className="text-center py-12 text-gray-500">
                                        <p>No transactions found</p>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* Payments Tab */}
                    <TabsContent value="payments">
                        <Card>
                            <CardHeader>
                                <CardTitle>Payment History</CardTitle>
                                <CardDescription>Recent receipt vouchers from this customer</CardDescription>
                            </CardHeader>
                            <CardContent>
                                {recent_payments.length > 0 ? (
                                    <div className="space-y-3">
                                        {recent_payments.map((payment, i) => (
                                            <div key={i} className="flex justify-between items-center p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                                                <div>
                                                    <div className="font-medium">{payment.date}</div>
                                                    <div className="text-sm text-gray-500">
                                                        {payment.voucher_number} {payment.narration && `• ${payment.narration}`}
                                                    </div>
                                                </div>
                                                <div className="text-green-600 font-bold text-lg">
                                                    {formatCurrency(payment.amount)}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="text-center py-12 text-gray-500">
                                        <p>No payment records found</p>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* Top Items Tab */}
                    <TabsContent value="items">
                        <Card>
                            <CardHeader>
                                <CardTitle>Top Purchased Items</CardTitle>
                                <CardDescription>Most frequently transacted items with this customer</CardDescription>
                            </CardHeader>
                            <CardContent>
                                {top_items.length > 0 ? (
                                    <table className="w-full">
                                        <thead>
                                            <tr className="border-b bg-gray-50">
                                                <th className="text-left py-3 px-4 text-sm font-medium">Item Name</th>
                                                <th className="text-right py-3 px-4 text-sm font-medium">Qty</th>
                                                <th className="text-right py-3 px-4 text-sm font-medium">Transactions</th>
                                                <th className="text-right py-3 px-4 text-sm font-medium">Avg Rate</th>
                                                <th className="text-right py-3 px-4 text-sm font-medium">Total Value</th>
                                                <th className="text-right py-3 px-4 text-sm font-medium">Last Date</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {top_items.map((item, i) => (
                                                <tr key={i} className="border-b hover:bg-gray-50 transition-colors">
                                                    <td className="py-3 px-4 font-medium">
                                                        <div className="flex items-center gap-2">
                                                            <Package className="h-4 w-4 text-gray-400" />
                                                            {item.item_name}
                                                        </div>
                                                    </td>
                                                    <td className="py-3 px-4 text-right">{item.total_quantity.toLocaleString()}</td>
                                                    <td className="py-3 px-4 text-right">{item.transaction_count}</td>
                                                    <td className="py-3 px-4 text-right">{formatCurrency(item.avg_rate)}</td>
                                                    <td className="py-3 px-4 text-right font-semibold">{formatCurrency(item.total_value)}</td>
                                                    <td className="py-3 px-4 text-right text-gray-500">{item.last_date || '-'}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                ) : (
                                    <div className="text-center py-12 text-gray-500">
                                        <Package className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                                        <p>No item history found</p>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* Analytics Tab */}
                    <TabsContent value="analytics">
                        <div className="grid grid-cols-2 gap-6">
                            {/* Monthly Trend Chart */}
                            <Card>
                                <CardHeader>
                                    <CardTitle>Monthly Trend</CardTitle>
                                    <CardDescription>Sales and receipts over time</CardDescription>
                                </CardHeader>
                                <CardContent>
                                    {monthly_trend.length > 0 ? (
                                        <div className="space-y-2">
                                            {monthly_trend.slice(-6).map((month, i) => (
                                                <div key={i} className="flex items-center gap-4">
                                                    <div className="w-16 text-sm text-gray-500">{month.label}</div>
                                                    <div className="flex-1">
                                                        <div className="flex gap-2 h-6">
                                                            <div
                                                                className="bg-blue-500 rounded"
                                                                style={{
                                                                    width: `${Math.min(100, (month.sales / Math.max(...monthly_trend.map(m => m.sales)) * 100) || 0)}%`,
                                                                    minWidth: month.sales > 0 ? '4px' : '0'
                                                                }}
                                                                title={`Sales: ${formatCurrency(month.sales)}`}
                                                            />
                                                            <div
                                                                className="bg-green-500 rounded"
                                                                style={{
                                                                    width: `${Math.min(100, (month.receipts / Math.max(...monthly_trend.map(m => m.receipts || 1)) * 100) || 0)}%`,
                                                                    minWidth: month.receipts > 0 ? '4px' : '0'
                                                                }}
                                                                title={`Receipts: ${formatCurrency(month.receipts)}`}
                                                            />
                                                        </div>
                                                    </div>
                                                    <div className="w-24 text-right text-sm font-medium">
                                                        {formatCurrency(month.sales)}
                                                    </div>
                                                </div>
                                            ))}
                                            <div className="flex gap-4 pt-4 text-sm">
                                                <div className="flex items-center gap-2">
                                                    <div className="w-3 h-3 bg-blue-500 rounded"></div>
                                                    <span>Sales</span>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <div className="w-3 h-3 bg-green-500 rounded"></div>
                                                    <span>Receipts</span>
                                                </div>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="text-center py-12 text-gray-500">
                                            <p>No trend data available</p>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>

                            {/* Summary Stats */}
                            <Card>
                                <CardHeader>
                                    <CardTitle>Summary Statistics</CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="p-4 bg-gray-50 rounded-lg">
                                            <p className="text-xs text-gray-500 uppercase">First Transaction</p>
                                            <p className="text-lg font-semibold">{summary.first_transaction_date || 'N/A'}</p>
                                        </div>
                                        <div className="p-4 bg-gray-50 rounded-lg">
                                            <p className="text-xs text-gray-500 uppercase">Last Transaction</p>
                                            <p className="text-lg font-semibold">{summary.last_transaction_date || 'N/A'}</p>
                                        </div>
                                        <div className="p-4 bg-gray-50 rounded-lg">
                                            <p className="text-xs text-gray-500 uppercase">Total Receipts</p>
                                            <p className="text-lg font-semibold text-green-600">{formatCurrency(summary.total_receipts)}</p>
                                        </div>
                                        <div className="p-4 bg-gray-50 rounded-lg">
                                            <p className="text-xs text-gray-500 uppercase">Avg Credit Days</p>
                                            <p className="text-lg font-semibold">{insights.avg_credit_days} days</p>
                                        </div>
                                    </div>

                                    {summary.credit_limit && summary.credit_limit > 0 && (
                                        <div className="p-4 bg-gray-50 rounded-lg">
                                            <div className="flex justify-between text-sm mb-2">
                                                <span className="text-gray-500">Credit Utilization</span>
                                                <span className="font-medium">{summary.credit_utilized_pct}%</span>
                                            </div>
                                            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                                                <div
                                                    className={`h-full rounded-full ${summary.credit_utilized_pct > 90 ? 'bg-red-500' :
                                                        summary.credit_utilized_pct > 70 ? 'bg-orange-500' :
                                                            'bg-green-500'
                                                        }`}
                                                    style={{ width: `${Math.min(100, summary.credit_utilized_pct)}%` }}
                                                />
                                            </div>
                                            <div className="flex justify-between text-xs text-gray-500 mt-1">
                                                <span>{formatCurrency(Math.abs(summary.current_balance))} used</span>
                                                <span>{formatCurrency(summary.credit_limit)} limit</span>
                                            </div>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        </div>
                    </TabsContent>
                </Tabs>
            </div>
        </div>
    );
}

export default function Customer360Page() {
    return (
        <Suspense fallback={
            <div className="flex h-screen items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            </div>
        }>
            <Customer360Content />
        </Suspense>
    );
}
