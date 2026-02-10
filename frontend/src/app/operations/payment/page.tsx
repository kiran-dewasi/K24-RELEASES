"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Check, Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function PaymentPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [formData, setFormData] = useState({
        party_name: "",
        amount: "",
        bank_cash_ledger: "Cash",
        narration: ""
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            const res = await fetch("http://localhost:8000/operations/payment", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "x-api-key": "k24-secret-key-123"
                },
                body: JSON.stringify(formData)
            });

            if (res.ok) {
                setSuccess(true);
                setTimeout(() => {
                    router.push("/daybook");
                }, 2000);
            } else {
                const err = await res.json();
                alert("Error: " + err.detail);
            }
        } catch (error) {
            console.error(error);
            alert("Failed to create payment");
        } finally {
            setLoading(false);
        }
    };

    if (success) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-green-50">
                <div className="text-center space-y-4">
                    <div className="h-16 w-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                        <Check className="h-8 w-8 text-green-600" />
                    </div>
                    <h2 className="text-2xl font-bold text-green-800">Payment Created!</h2>
                    <p className="text-green-600">Redirecting to dashboard...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[#FAFAF8] text-[#1A1A1A] font-sans p-6">
            <div className="max-w-md mx-auto space-y-6">
                <div className="flex items-center gap-4">
                    <Link href="/" className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                        <ArrowLeft className="h-5 w-5 text-gray-500" />
                    </Link>
                    <h1 className="text-xl font-semibold">New Payment</h1>
                </div>

                <Card className="border-none shadow-sm bg-white">
                    <CardContent className="p-6">
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-gray-700">Paid To (Party)</label>
                                <input
                                    type="text"
                                    required
                                    className="w-full p-2 border rounded-md focus:ring-2 focus:ring-orange-500 outline-none"
                                    placeholder="e.g. Vendor X"
                                    value={formData.party_name}
                                    onChange={e => setFormData({ ...formData, party_name: e.target.value })}
                                />
                            </div>

                            <div className="space-y-2">
                                <label className="text-sm font-medium text-gray-700">Amount (₹)</label>
                                <input
                                    type="number"
                                    required
                                    className="w-full p-2 border rounded-md focus:ring-2 focus:ring-orange-500 outline-none"
                                    placeholder="0.00"
                                    value={formData.amount}
                                    onChange={e => setFormData({ ...formData, amount: e.target.value })}
                                />
                            </div>

                            <div className="space-y-2">
                                <label className="text-sm font-medium text-gray-700">Paid From</label>
                                <select
                                    className="w-full p-2 border rounded-md focus:ring-2 focus:ring-orange-500 outline-none"
                                    value={formData.bank_cash_ledger}
                                    onChange={e => setFormData({ ...formData, bank_cash_ledger: e.target.value })}
                                >
                                    <option value="Cash">Cash</option>
                                    <option value="HDFC Bank">HDFC Bank</option>
                                    <option value="SBI Bank">SBI Bank</option>
                                </select>
                            </div>

                            <div className="space-y-2">
                                <label className="text-sm font-medium text-gray-700">Narration</label>
                                <textarea
                                    className="w-full p-2 border rounded-md focus:ring-2 focus:ring-orange-500 outline-none"
                                    placeholder="Optional notes..."
                                    rows={3}
                                    value={formData.narration}
                                    onChange={e => setFormData({ ...formData, narration: e.target.value })}
                                />
                            </div>

                            <button
                                type="submit"
                                disabled={loading}
                                className="w-full py-2 bg-orange-600 text-white rounded-md font-medium hover:bg-orange-700 transition-colors flex items-center justify-center gap-2"
                            >
                                {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                                {loading ? "Creating..." : "Create Payment"}
                            </button>
                        </form>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
