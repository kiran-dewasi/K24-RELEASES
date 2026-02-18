"use client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

import { useState, useEffect, Suspense } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Building2, Mail, Phone, MapPin, TrendingUp, TrendingDown, Clock, ArrowRight, Plus, Loader2 } from "lucide-react";

interface Voucher {
    date: string;
    voucher_type: string;
    voucher_number: string;
    amount: number;
    narration: string;
}

interface ContactDetails {
    name: string;
    gstin?: string;
    address?: string;
    email?: string;
    phone?: string;
    opening_balance?: number;
}




function ContactProfileContent() {
    const params = useParams();
    const router = useRouter();
    const ledgerName = decodeURIComponent(params.name as string);

    const [vouchers, setVouchers] = useState<Voucher[]>([]);
    const [contactDetails, setContactDetails] = useState<ContactDetails | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                // Fetch vouchers
                const vouchersRes = await fetch(`${API_URL}/ledgers/${encodeURIComponent(ledgerName)}/vouchers`, {
                    headers: { "x-api-key": "k24-secret-key-123" }
                });
                const vouchersData = await vouchersRes.json();
                setVouchers(vouchersData.vouchers || []);

                // Fetch contact details
                const detailsRes = await fetch(`${API_URL}/customer-details/`, {
                    method: "POST",
                    headers: {
                        "x-api-key": "k24-secret-key-123",
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ name: ledgerName })
                });
                const detailsData = await detailsRes.json();
                setContactDetails({
                    name: ledgerName,
                    gstin: detailsData.details?.GSTIN,
                    address: detailsData.details?.ADDRESS,
                    email: detailsData.details?.EMAIL,
                    phone: detailsData.details?.PHONE,
                    opening_balance: detailsData.details?.OPENING_BALANCE
                });
            } catch (error) {
                console.error("Failed to fetch contact data", error);
            } finally {
                setLoading(false);
            }
        };
        if (ledgerName && ledgerName !== 'default') fetchData();
    }, [ledgerName]);

    // Calculate Stats
    const totalSales = vouchers.filter(v => v.voucher_type === "Sales").reduce((sum, v) => sum + v.amount, 0);
    const totalPurchases = vouchers.filter(v => v.voucher_type === "Purchase").reduce((sum, v) => sum + v.amount, 0);
    const totalReceipts = vouchers.filter(v => v.voucher_type === "Receipt").reduce((sum, v) => sum + v.amount, 0);
    const totalPayments = vouchers.filter(v => v.voucher_type === "Payment").reduce((sum, v) => sum + v.amount, 0);
    const outstandingBalance = totalSales - totalReceipts - totalPurchases + totalPayments;

    if (ledgerName === 'default') {
        return <div className="p-8 text-center text-muted-foreground">Select a contact to view profile.</div>;
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 py-8 px-4 sm:px-6 lg:px-8">
            <div className="max-w-6xl mx-auto space-y-6">

                {/* Header with Profile Info */}
                <div className="bg-white rounded-2xl shadow-lg p-8">
                    <div className="flex items-start justify-between">
                        <div className="flex gap-6">
                            <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center text-white font-bold text-3xl shadow-lg">
                                {ledgerName.charAt(0).toUpperCase()}
                            </div>
                            <div className="space-y-2">
                                <h1 className="text-4xl font-bold text-gray-900">{ledgerName}</h1>

                                <div className="flex gap-6 text-sm text-gray-600">
                                    {contactDetails?.gstin && (
                                        <div className="flex items-center gap-2">
                                            <Building2 className="h-4 w-4" />
                                            <span>GSTIN: {contactDetails.gstin}</span>
                                        </div>
                                    )}
                                    {contactDetails?.phone && (
                                        <div className="flex items-center gap-2">
                                            <Phone className="h-4 w-4" />
                                            <span>{contactDetails.phone}</span>
                                        </div>
                                    )}
                                    {contactDetails?.email && (
                                        <div className="flex items-center gap-2">
                                            <Mail className="h4 w-4" />
                                            <span>{contactDetails.email}</span>
                                        </div>
                                    )}
                                </div>

                                {contactDetails?.address && (
                                    <div className="flex items-start gap-2 text-sm text-gray-500">
                                        <MapPin className="h-4 w-4 mt-0.5 flex-shrink-0" />
                                        <span>{contactDetails.address}</span>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Quick Actions */}
                        <div className="flex gap-2">
                            <Button
                                onClick={() => router.push(`/vouchers/new/sales?party=${encodeURIComponent(ledgerName)}`)}
                                className="bg-green-600 hover:bg-green-700"
                            >
                                <Plus className="h-4 w-4 mr-2" />
                                New Sale
                            </Button>
                            <Button
                                onClick={() => router.push(`/vouchers/new/receipt?party=${encodeURIComponent(ledgerName)}`)}
                                variant="outline"
                            >
                                <Plus className="h-4 w-4 mr-2" />
                                Receipt
                            </Button>
                        </div>
                    </div>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
                        <CardContent className="pt-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm font-medium text-blue-700">Total Sales</p>
                                    <p className="text-2xl font-bold text-blue-900">₹{totalSales.toLocaleString('en-IN')}</p>
                                </div>
                                <TrendingUp className="h-8 w-8 text-blue-500" />
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
                        <CardContent className="pt-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm font-medium text-purple-700">Total Purchases</p>
                                    <p className="text-2xl font-bold text-purple-900">₹{totalPurchases.toLocaleString('en-IN')}</p>
                                </div>
                                <TrendingDown className="h-8 w-8 text-purple-500" />
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
                        <CardContent className="pt-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm font-medium text-green-700">Total Received</p>
                                    <p className="text-2xl font-bold text-green-900">₹{totalReceipts.toLocaleString('en-IN')}</p>
                                </div>
                                <Clock className="h-8 w-8 text-green-500" />
                            </div>
                        </CardContent>
                    </Card>

                    <Card className={`bg-gradient-to-br ${outstandingBalance > 0 ? 'from-orange-50 to-orange-100 border-orange-200' : 'from-gray-50 to-gray-100 border-gray-200'}`}>
                        <CardContent className="pt-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className={`text-sm font-medium ${outstandingBalance > 0 ? 'text-orange-700' : 'text-gray-700'}`}>Outstanding</p>
                                    <p className={`text-2xl font-bold ${outstandingBalance > 0 ? 'text-orange-900' : 'text-gray-900'}`}>
                                        ₹{Math.abs(outstandingBalance).toLocaleString('en-IN')}
                                    </p>
                                </div>
                                <ArrowRight className={`h-8 w-8 ${outstandingBalance > 0 ? 'text-orange-500' : 'text-gray-500'}`} />
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Transaction Timeline */}
                <Card className="bg-white shadow-lg">
                    <CardHeader className="border-b bg-gray-50">
                        <CardTitle className="text-xl">Transaction Timeline</CardTitle>
                    </CardHeader>
                    <CardContent className="pt-6">
                        {loading ? (
                            <div className="flex items-center justify-center py-12">
                                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                            </div>
                        ) : vouchers.length === 0 ? (
                            <div className="text-center py-12 text-gray-500">
                                <p className="text-lg font-medium">No transactions yet</p>
                                <p className="text-sm mt-2">Start by creating a sale or receipt</p>
                            </div>
                        ) : (
                            <div className="space-y-1">
                                {vouchers.map((v, idx) => (
                                    <div
                                        key={idx}
                                        className="flex items-center justify-between p-4 hover:bg-gray-50 rounded-lg transition-colors cursor-pointer group"
                                    >
                                        <div className="flex items-center gap-4 flex-1">
                                            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${v.voucher_type === 'Sales' ? 'bg-blue-100 text-blue-600' :
                                                v.voucher_type === 'Purchase' ? 'bg-purple-100 text-purple-600' :
                                                    v.voucher_type === 'Receipt' ? 'bg-green-100 text-green-600' :
                                                        'bg-orange-100 text-orange-600'
                                                }`}>
                                                {v.voucher_type === 'Sales' ? '📄' :
                                                    v.voucher_type === 'Purchase' ? '🛒' :
                                                        v.voucher_type === 'Receipt' ? '💰' : '💸'}
                                            </div>
                                            <div className="flex-1">
                                                <div className="flex items-center gap-3">
                                                    <p className="font-semibold text-gray-900">{v.voucher_type}</p>
                                                    <span className="text-xs bg-gray-100 px-2 py-1 rounded-full text-gray-600">
                                                        #{v.voucher_number}
                                                    </span>
                                                </div>
                                                <div className="flex items-center gap-4 mt-1">
                                                    <p className="text-sm text-gray-500">{new Date(v.date).toLocaleDateString('en-IN')}</p>
                                                    {v.narration && (
                                                        <p className="text-sm text-gray-400 italic truncate max-w-md">{v.narration}</p>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                        <div className={`text-right ${v.voucher_type === 'Receipt' || v.voucher_type === 'Sales' ? 'text-green-600' :
                                            v.voucher_type === 'Payment' || v.voucher_type === 'Purchase' ? 'text-red-600' :
                                                'text-gray-900'
                                            }`}>
                                            <p className="text-xl font-bold">
                                                {v.voucher_type === 'Receipt' || v.voucher_type === 'Sales' ? '+' : '-'}
                                                ₹{v.amount.toLocaleString('en-IN')}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>

            </div>
        </div>
    );
}

export default function ContactProfilePage() {
    return (
        <Suspense fallback={
            <div className="flex h-screen items-center justify-center">
                <Loader2 className="animate-spin h-8 w-8 text-muted-foreground" />
            </div>
        }>
            <ContactProfileContent />
        </Suspense>
    );
}
