"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Loader2 } from "lucide-react";
import { apiRequest } from "@/lib/api";

interface PaymentAccount {
    name: string;
}

export default function NewPaymentClient() {
    const router = useRouter();
    const searchParams = useSearchParams();

    // Form State
    const [partyName, setPartyName] = useState(searchParams.get("party") || "");
    const [amount, setAmount] = useState(searchParams.get("amount") || "");
    const [payFrom, setPayFrom] = useState("Cash");
    const [narration, setNarration] = useState("");
    const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
    const [gstRate, setGstRate] = useState<number>(0);
    const [gstAsExpense, setGstAsExpense] = useState<boolean>(false);

    // UI State
    const [loading, setLoading] = useState(false);
    const [partySuggestions, setPartySuggestions] = useState<string[]>([]);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);
    const [paymentAccounts, setPaymentAccounts] = useState<PaymentAccount[]>([
        { name: "Cash" },
        { name: "Bank" }
    ]);

    // Fetch party suggestions as user types
    useEffect(() => {
        if (partyName.length < 2) {
            setPartySuggestions([]);
            return;
        }

        const fetchSuggestions = async () => {
            try {
                const data = await apiRequest<{ matches: string[] }>(
                    `/ledgers/search?query=${encodeURIComponent(partyName)}`
                );
                setPartySuggestions(data.matches || []);
                setShowSuggestions(true);
            } catch (error) {
                console.error("Failed to fetch suggestions", error);
            }
        };

        const debounce = setTimeout(fetchSuggestions, 300);
        return () => clearTimeout(debounce);
    }, [partyName]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);

        try {
            const data = await apiRequest('/vouchers/payment', 'POST', {
                party_name: partyName,
                amount: parseFloat(amount),
                bank_cash_ledger: payFrom, // Backend expects this field name
                narration,
                date,
                gst_rate: gstRate,
                gst_is_expense: gstAsExpense
            });

            // Success
            alert("Payment created successfully!");
            router.push("/daybook");
        } catch (error: any) {
            console.error("Failed to create payment", error);
            setErrorMsg(error?.message || "Failed to connect to backend. Please check if K24 is running.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 p-8">
            <div className="max-w-2xl mx-auto space-y-6">
                {/* Header */}
                <div className="flex items-center gap-4">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => router.back()}
                    >
                        <ArrowLeft className="h-5 w-5" />
                    </Button>
                    <h1 className="text-3xl font-bold tracking-tight text-red-700">New Payment</h1>
                </div>

                {/* Error Display */}
                {errorMsg && (
                    <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
                        <strong className="font-bold">Error: </strong>
                        <span className="block sm:inline">{errorMsg}</span>
                    </div>
                )}

                {/* Form Card */}
                <Card className="border-t-4 border-t-red-600">
                    <CardContent className="pt-6">
                        <form onSubmit={handleSubmit} className="space-y-6">
                            {/* Party Name */}
                            <div className="space-y-2 relative">
                                <label className="text-sm font-medium">
                                    Paid To (Party)
                                </label>
                                <input
                                    type="text"
                                    placeholder="e.g. Supplier B"
                                    value={partyName}
                                    onChange={(e) => setPartyName(e.target.value)}
                                    onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                                    onFocus={() => partySuggestions.length > 0 && setShowSuggestions(true)}
                                    required
                                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                                />

                                {/* Autocomplete Suggestions */}
                                {showSuggestions && partySuggestions.length > 0 && (
                                    <div className="absolute z-10 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-60 overflow-y-auto">
                                        {partySuggestions.map((suggestion, idx) => (
                                            <button
                                                key={idx}
                                                type="button"
                                                onClick={() => {
                                                    setPartyName(suggestion);
                                                    setShowSuggestions(false);
                                                }}
                                                className="w-full px-4 py-2 text-left hover:bg-gray-100 transition-colors"
                                            >
                                                {suggestion}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/* Amount */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium">
                                    Amount (₹)
                                </label>
                                <input
                                    type="number"
                                    step="0.01"
                                    placeholder="0.00"
                                    value={amount}
                                    onChange={(e) => setAmount(e.target.value)}
                                    required
                                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                                />
                            </div>

                            {/* Date */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium">
                                    Date
                                </label>
                                <input
                                    type="date"
                                    value={date}
                                    onChange={(e) => setDate(e.target.value)}
                                    required
                                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                                />
                            </div>

                            {/* GST Rate */}
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="text-sm font-medium">GST Rate</label>
                                    <select
                                        value={gstRate}
                                        onChange={(e) => setGstRate(Number(e.target.value))}
                                        className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent bg-white"
                                    >
                                        <option value={0}>Exempt (0%)</option>
                                        <option value={5}>5%</option>
                                        <option value={12}>12%</option>
                                        <option value={18}>18%</option>
                                        <option value={28}>28%</option>
                                    </select>
                                </div>

                                <div className="flex items-end pb-3">
                                    <label className="flex items-center space-x-2 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={gstAsExpense}
                                            onChange={(e) => setGstAsExpense(e.target.checked)}
                                            className="w-5 h-5 text-red-600 rounded focus:ring-red-500"
                                        />
                                        <span className="text-sm font-medium text-gray-700">
                                            Treat GST as Expense
                                        </span>
                                    </label>
                                </div>
                            </div>

                            {/* Summary Display */}
                            {gstRate > 0 && (
                                <div className="bg-gray-100 p-3 rounded text-sm space-y-1">
                                    <div className="flex justify-between">
                                        <span>Base Amount:</span>
                                        <span>₹{parseFloat(amount || "0").toFixed(2)}</span>
                                    </div>
                                    <div className="flex justify-between text-gray-600">
                                        <span>Tax ({gstRate}%):</span>
                                        <span>₹{((parseFloat(amount || "0") * gstRate) / 100).toFixed(2)}</span>
                                    </div>
                                    <div className="flex justify-between font-bold border-t pt-1 mt-1">
                                        <span>Total:</span>
                                        <span>₹{(parseFloat(amount || "0") * (1 + gstRate / 100)).toFixed(2)}</span>
                                    </div>
                                    <div className="text-xs text-blue-600 pt-1">
                                        {gstAsExpense
                                            ? "ℹ️ Tax added to Party/Expense cost (No Input Credit)"
                                            : "ℹ️ Tax booked separately for Input Credit"}
                                    </div>
                                </div>
                            )}

                            {/* Pay From */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium">
                                    Pay From
                                </label>
                                <select
                                    value={payFrom}
                                    onChange={(e) => setPayFrom(e.target.value)}
                                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent bg-white"
                                >
                                    {paymentAccounts.map((acc) => (
                                        <option key={acc.name} value={acc.name}>
                                            {acc.name}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {/* Narration */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium">
                                    Narration
                                </label>
                                <textarea
                                    placeholder="Optional notes..."
                                    value={narration}
                                    onChange={(e) => setNarration(e.target.value)}
                                    rows={4}
                                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent resize-none"
                                />
                            </div>

                            {/* Submit Button */}
                            <Button
                                type="submit"
                                disabled={loading}
                                className="w-full bg-red-600 hover:bg-red-700 text-white py-6 text-lg font-medium"
                            >
                                {loading ? (
                                    <>
                                        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                        Creating Payment...
                                    </>
                                ) : (
                                    "Create Payment"
                                )}
                            </Button>
                        </form>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
