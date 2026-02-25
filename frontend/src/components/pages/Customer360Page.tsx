'use client';

import { useEffect, useState, Suspense } from 'react';
import { apiClient } from '@/lib/api';
import { useSearchParams, useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
    ArrowLeft, Phone, Mail, MapPin, FileText, Download,
    TrendingUp, TrendingDown, AlertTriangle, CheckCircle,
    Clock, CreditCard, Package, BarChart3, RefreshCw, Loader2, X, ChevronRight
} from 'lucide-react';

// --- Voucher Detail Types ---
interface VoucherLineItem {
    name: string;
    quantity: number;
    rate: number;
    amount: number;
    godown?: string;
    batch?: string;
}
interface VoucherDetail {
    voucher_number: string;
    date: string;
    voucher_type: string;
    party_name: string;
    narration: string;
    items: VoucherLineItem[];
    ledgers: { name: string; amount: number; is_tax: boolean }[];
    tax_breakdown: { name: string; amount: number }[];
    total_amount: number;
    source?: string;
}

// --- Voucher Detail Modal ---
function VoucherDetailModal({
    voucher,
    loading,
    onClose,
}: {
    voucher: VoucherDetail | null;
    loading: boolean;
    onClose: () => void;
}) {
    const fmt = (n: number) =>
        `₹${Math.abs(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    const typeColor: Record<string, string> = {
        Sales: 'bg-blue-100 text-blue-700',
        Purchase: 'bg-purple-100 text-purple-700',
        Receipt: 'bg-green-100 text-green-700',
        Payment: 'bg-orange-100 text-orange-700',
    };

    return (
        <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center" onClick={onClose}>
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
            {/* Panel */}
            <div
                className="relative w-full max-w-2xl mx-4 bg-white rounded-t-2xl sm:rounded-2xl shadow-2xl max-h-[85vh] overflow-hidden flex flex-col animate-in slide-in-from-bottom-4 duration-300"
                onClick={e => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b bg-gradient-to-r from-slate-800 to-slate-700">
                    <div>
                        <div className="flex items-center gap-3">
                            <span className="text-white font-bold text-lg">
                                {loading ? 'Loading…' : (voucher?.voucher_number || '—')}
                            </span>
                            {voucher && (
                                <span className={`text-xs font-semibold px-2 py-1 rounded-full ${typeColor[voucher.voucher_type] || 'bg-gray-100 text-gray-700'}`}>
                                    {voucher.voucher_type}
                                </span>
                            )}
                        </div>
                        {voucher && (
                            <p className="text-slate-300 text-sm mt-0.5">
                                {voucher.party_name} · {voucher.date}
                            </p>
                        )}
                    </div>
                    <button
                        onClick={onClose}
                        className="text-slate-400 hover:text-white rounded-full p-1 transition-colors"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>

                {/* Body */}
                <div className="overflow-y-auto flex-1 p-6">
                    {loading && (
                        <div className="flex flex-col items-center justify-center py-16">
                            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mb-3" />
                            <p className="text-gray-500 text-sm">Fetching voucher details from Tally…</p>
                        </div>
                    )}

                    {!loading && !voucher && (
                        <div className="text-center py-16">
                            <AlertTriangle className="h-10 w-10 text-orange-400 mx-auto mb-3" />
                            <p className="text-gray-600 font-medium">Voucher details not available</p>
                            <p className="text-gray-400 text-sm mt-1">Tally may not have returned line items for this voucher type.</p>
                        </div>
                    )}

                    {!loading && voucher && (
                        <div className="space-y-5">
                            {/* Narration */}
                            {voucher.narration && (
                                <div className="bg-slate-50 rounded-lg p-3 text-sm text-slate-600 italic">
                                    {voucher.narration}
                                </div>
                            )}

                            {/* Line Items */}
                            {voucher.items.length > 0 ? (
                                <div>
                                    <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3 flex items-center gap-2">
                                        <Package className="h-4 w-4" /> Items ({voucher.items.length})
                                    </h3>
                                    <div className="rounded-xl border overflow-hidden">
                                        <table className="w-full text-sm">
                                            <thead className="bg-slate-50">
                                                <tr>
                                                    <th className="text-left py-2 px-3 font-medium text-slate-600">#</th>
                                                    <th className="text-left py-2 px-3 font-medium text-slate-600">Item</th>
                                                    <th className="text-right py-2 px-3 font-medium text-slate-600">Qty</th>
                                                    <th className="text-right py-2 px-3 font-medium text-slate-600">Rate</th>
                                                    <th className="text-right py-2 px-3 font-medium text-slate-600">Amount</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {voucher.items.map((item, i) => (
                                                    <tr key={i} className="border-t hover:bg-slate-50">
                                                        <td className="py-3 px-3 text-slate-400">{i + 1}</td>
                                                        <td className="py-3 px-3">
                                                            <p className="font-medium text-slate-800">{item.name}</p>
                                                            {item.godown && item.godown !== 'Main Location' && (
                                                                <p className="text-xs text-slate-400">{item.godown}</p>
                                                            )}
                                                        </td>
                                                        <td className="py-3 px-3 text-right text-slate-600">{item.quantity}</td>
                                                        <td className="py-3 px-3 text-right text-slate-600">{fmt(item.rate)}</td>
                                                        <td className="py-3 px-3 text-right font-semibold text-slate-800">{fmt(item.amount)}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            ) : (
                                <div className="border border-dashed rounded-lg p-6 text-center text-slate-400">
                                    <Package className="h-8 w-8 mx-auto mb-2 opacity-40" />
                                    <p className="text-sm">No inventory items on this voucher</p>
                                    <p className="text-xs mt-1">(Receipt / Payment vouchers don't carry stock entries)</p>
                                </div>
                            )}

                            {/* Ledger Entries */}
                            {voucher.ledgers.length > 0 && (
                                <div>
                                    <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3 flex items-center gap-2">
                                        <CreditCard className="h-4 w-4" /> Accounting Entries
                                    </h3>
                                    <div className="space-y-1">
                                        {voucher.ledgers.map((led, i) => (
                                            <div key={i} className={`flex justify-between items-center px-3 py-2 rounded-lg text-sm ${led.is_tax ? 'bg-amber-50 text-amber-700' : 'bg-slate-50 text-slate-700'
                                                }`}>
                                                <span className="font-medium">{led.name}</span>
                                                <span className={`font-mono font-semibold ${led.amount < 0 ? 'text-green-600' : 'text-red-600'
                                                    }`}>
                                                    {led.amount < 0 ? 'Cr ' : 'Dr '}{fmt(Math.abs(led.amount))}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Total */}
                            <div className="border-t pt-4 flex justify-between items-center">
                                <span className="text-base font-semibold text-slate-700">Total Amount</span>
                                <span className="text-xl font-bold text-slate-900">{fmt(voucher.total_amount)}</span>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

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
        balance_type?: string;
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

    // Voucher detail modal state
    const [selectedVoucher, setSelectedVoucher] = useState<VoucherDetail | null>(null);
    const [voucherModalOpen, setVoucherModalOpen] = useState(false);
    const [voucherLoading, setVoucherLoading] = useState(false);

    const openVoucherDetail = async (voucherNumber: string, voucherType: string) => {
        setSelectedVoucher(null);
        setVoucherModalOpen(true);
        setVoucherLoading(true);
        try {
            const params = new URLSearchParams({ voucher_number: voucherNumber, voucher_type: voucherType });
            const res = await apiClient(`/api/vouchers/detail?${params}`);
            if (res.ok) {
                const detail = await res.json();
                setSelectedVoucher(detail);
            }
        } catch (err) {
            console.error('Failed to fetch voucher detail:', err);
        } finally {
            setVoucherLoading(false);
        }
    };

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await apiClient(`/api/customers/${id}/360`);

            if (!res.ok) {
                if (res.status === 404) {
                    setError('Customer not found');
                } else {
                    const errBody = await res.json().catch(() => ({}));
                    setError(errBody.detail || 'Failed to load customer data');
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

    const handleExport = () => {
        if (!data) return;
        const { customer, recent_transactions, outstanding_bills, summary } = data;

        // Sheet 1: Summary
        const summaryRows = [
            ['Customer 360° Export'],
            ['Name', customer.name],
            ['Group', customer.group || ''],
            ['GSTIN', customer.gstin || ''],
            ['Phone', customer.phone || ''],
            ['Closing Balance', summary.current_balance.toFixed(2)],
            ['Total Sales', summary.total_sales.toFixed(2)],
            ['Total Purchases', summary.total_purchases.toFixed(2)],
            ['Outstanding Total', summary.outstanding_total.toFixed(2)],
            ['Overdue Total', summary.overdue_total.toFixed(2)],
            ['Transaction Count', summary.transaction_count],
            [],
            ['--- RECENT TRANSACTIONS ---'],
            ['Date', 'Voucher No', 'Type', 'Amount', 'Narration'],
            ...recent_transactions.map(t => [
                t.date,
                t.voucher_number,
                t.voucher_type,
                t.amount.toFixed(2),
                t.narration || ''
            ]),
            [],
            ['--- OUTSTANDING BILLS ---'],
            ['Bill Name', 'Amount', 'Pending', 'Due Date', 'Overdue Days', 'Aging'],
            ...outstanding_bills.map(b => [
                b.bill_name,
                b.amount.toFixed(2),
                b.pending_amount.toFixed(2),
                b.due_date || '',
                b.overdue_days,
                b.aging_bucket
            ])
        ];

        const csv = summaryRows
            .map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(','))
            .join('\n');
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${customer.name.replace(/[^a-z0-9]/gi, '_')}_360_profile.csv`;
        a.click();
        URL.revokeObjectURL(url);
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
                            <Button variant="outline" size="sm" onClick={handleExport}>
                                <Download className="h-4 w-4 mr-2" />
                                Export
                            </Button>
                            <Button
                                size="sm"
                                className="bg-blue-600 hover:bg-blue-700"
                                onClick={() => router.push(`/vouchers/new/sales?party=${encodeURIComponent(customer.name)}`)}
                            >
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
                            subtitle={
                                // Use balance_type from Tally if available, else infer from group
                                customer.balance_type === 'Cr' || (customer.group || '').toLowerCase().includes('creditor')
                                    ? 'Payable (Cr)'
                                    : 'Receivable (Dr)'
                            }
                            icon={<CreditCard className="h-6 w-6" />}
                            color={
                                customer.balance_type === 'Cr' || (customer.group || '').toLowerCase().includes('creditor')
                                    ? 'orange'
                                    : 'green'
                            }
                        />
                        <MetricCard
                            title={
                                (customer.group || '').toLowerCase().includes('creditor')
                                    ? 'Total Purchases'
                                    : 'Total Sales'
                            }
                            value={
                                (customer.group || '').toLowerCase().includes('creditor')
                                    ? formatCurrency(summary.total_purchases)
                                    : formatCurrency(summary.total_sales)
                            }
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
                                <p className="text-xs text-blue-600 mb-3 flex items-center gap-1">
                                    <ChevronRight className="h-3 w-3" /> Click any row to view full voucher detail
                                </p>
                                <table className="w-full">
                                    <thead>
                                        <tr className="border-b bg-gray-50">
                                            <th className="text-left py-3 px-4 text-sm font-medium">Date</th>
                                            <th className="text-left py-3 px-4 text-sm font-medium">Voucher #</th>
                                            <th className="text-left py-3 px-4 text-sm font-medium">Type</th>
                                            <th className="text-left py-3 px-4 text-sm font-medium">Narration</th>
                                            <th className="text-right py-3 px-4 text-sm font-medium">Amount</th>
                                            <th className="py-3 px-4"></th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {recent_transactions.map((txn, i) => (
                                            <tr
                                                key={i}
                                                className="border-b hover:bg-blue-50 transition-colors cursor-pointer group"
                                                onClick={() => openVoucherDetail(txn.voucher_number, txn.voucher_type)}
                                                title="Click to view details"
                                            >
                                                <td className="py-3 px-4 text-sm">{txn.date}</td>
                                                <td className="py-3 px-4 font-mono text-sm text-blue-600 group-hover:underline">{txn.voucher_number}</td>
                                                <td className="py-3 px-4">
                                                    <Badge variant="outline">{txn.voucher_type}</Badge>
                                                </td>
                                                <td className="py-3 px-4 text-gray-600 text-sm max-w-xs truncate">
                                                    {txn.narration || '-'}
                                                </td>
                                                <td className="py-3 px-4 text-right font-mono font-semibold">
                                                    {formatCurrency(txn.amount)}
                                                </td>
                                                <td className="py-3 px-4 text-right">
                                                    <ChevronRight className="h-4 w-4 text-gray-300 group-hover:text-blue-500 ml-auto" />
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
                                            {monthly_trend.slice(-6).map((month, i) => {
                                                // For creditors: show payments+purchases; for debtors: sales+receipts
                                                const isCreditor = (customer.group || '').toLowerCase().includes('creditor');
                                                const monthTotal = isCreditor
                                                    ? (month.payments || 0) + (month.purchases || 0)
                                                    : (month.sales || 0) + (month.receipts || 0);
                                                return (
                                                    <div key={i} className="flex items-center gap-4">
                                                        <div className="w-16 text-sm text-gray-500">{month.label}</div>
                                                        <div className="flex-1">
                                                            <div className="flex gap-2 h-6">
                                                                <div
                                                                    className="bg-blue-500 rounded"
                                                                    style={{
                                                                        width: `${Math.min(100, (month.sales / Math.max(...monthly_trend.map(m => m.sales || 1)) * 100) || 0)}%`,
                                                                        minWidth: month.sales > 0 ? '4px' : '0'
                                                                    }}
                                                                    title={`Sales: ${formatCurrency(month.sales)}`}
                                                                />
                                                                <div
                                                                    className="bg-green-500 rounded"
                                                                    style={{
                                                                        width: `${Math.min(100, ((month.receipts || 0) / Math.max(...monthly_trend.map(m => m.receipts || 1)) * 100) || 0)}%`,
                                                                        minWidth: (month.receipts || 0) > 0 ? '4px' : '0'
                                                                    }}
                                                                    title={`Receipts: ${formatCurrency(month.receipts)}`}
                                                                />
                                                                <div
                                                                    className="bg-orange-400 rounded"
                                                                    style={{
                                                                        width: `${Math.min(100, ((month.payments || 0) / Math.max(...monthly_trend.map(m => m.payments || 1)) * 100) || 0)}%`,
                                                                        minWidth: (month.payments || 0) > 0 ? '4px' : '0'
                                                                    }}
                                                                    title={`Payments: ${formatCurrency(month.payments)}`}
                                                                />
                                                            </div>
                                                        </div>
                                                        <div className="w-28 text-right text-sm font-medium">
                                                            {formatCurrency(monthTotal)}
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                            <div className="flex gap-4 pt-4 text-sm">
                                                <div className="flex items-center gap-2">
                                                    <div className="w-3 h-3 bg-blue-500 rounded"></div>
                                                    <span>Sales</span>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <div className="w-3 h-3 bg-green-500 rounded"></div>
                                                    <span>Receipts</span>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <div className="w-3 h-3 bg-orange-400 rounded"></div>
                                                    <span>Payments</span>
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

            {/* Voucher Detail Modal */}
            {voucherModalOpen && (
                <VoucherDetailModal
                    voucher={selectedVoucher}
                    loading={voucherLoading}
                    onClose={() => {
                        setVoucherModalOpen(false);
                        setSelectedVoucher(null);
                    }}
                />
            )}
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
