"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Loader2 } from "lucide-react";
import { API_CONFIG } from "@/lib/api-config";

interface DepositAccount {
    name: string;
}

export default function NewReceiptClient() {
    const router = useRouter();
    const searchParams = useSearchParams();

    // Form State
    const [partyName, setPartyName] = useState(searchParams.get("party") || "");
    const [amount, setAmount] = useState(searchParams.get("amount") || "");
    const [depositTo, setDepositTo] = useState("Cash");
    const [narration, setNarration] = useState("");
    const [date, setDate] = useState(new Date().toISOString().split('T')[0]);

    // UI State
    const [loading, setLoading] = useState(false);
    const [partySuggestions, setPartySuggestions] = useState<string[]>([]);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);
    const [depositAccounts, setDepositAccounts] = useState<DepositAccount[]>([
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
                const res = await fetch(`${API_CONFIG.BASE_URL}/ledgers/search?query=${encodeURIComponent(partyName)}`, {
                    headers: { "x-api-key": "k24-secret-key-123" }
                });
                const data = await res.json();
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
        setErrorMsg(null);

        try {
            // Use API_CONFIG for reliable connection
            const res = await fetch(`${API_CONFIG.BASE_URL}/vouchers/receipt`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "x-api-key": "k24-secret-key-123"
                },
                body: JSON.stringify({
                    party_name: partyName,
                    amount: parseFloat(amount),
                    deposit_to: depositTo,
                    narration,
                    date
                })
            });

            const data = await res.json();

            if (res.ok) {
                // Success
                alert("Receipt created successfully!");
                router.push("/daybook");
            } else {
                setErrorMsg(data.detail || "Failed to create receipt via Tally");
            }
        } catch (error) {
            console.error("Network/Client Error:", error);
            setErrorMsg(`Network Error: ${error}`);
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
                    <h1 className="text-3xl font-bold tracking-tight">New Receipt</h1>
                </div>

                {/* Error Display */}
                {errorMsg && (
                    <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
                        <strong className="font-bold">Error: </strong>
                        <span className="block sm:inline">{errorMsg}</span>
                    </div>
                )}

                {/* Form Card */}
                <Card>
                    <CardContent className="pt-6">
                        <form onSubmit={handleSubmit} className="space-y-6">
                            {/* ... rest of the form ... */}
                            {/* Party Name */}
                            <div className="space-y-2 relative">
                                <label className="text-sm font-medium">
                                    Received From (Party)
                                </label>
                                <input
                                    type="text"
                                    placeholder="e.g. Customer A"
                                    value={partyName}
                                    onChange={(e) => setPartyName(e.target.value)}
                                    onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                                    onFocus={() => partySuggestions.length > 0 && setShowSuggestions(true)}
                                    required
                                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
                                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
                                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                />
                            </div>

                            {/* Deposit To */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium">
                                    Deposit To
                                </label>
                                <select
                                    value={depositTo}
                                    onChange={(e) => setDepositTo(e.target.value)}
                                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
                                >
                                    {depositAccounts.map((acc) => (
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
                                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                                />
                            </div>

                            {/* Submit Button */}
                            <Button
                                type="submit"
                                disabled={loading}
                                className="w-full bg-blue-600 hover:bg-blue-700 text-white py-6 text-lg font-medium"
                            >
                                {loading ? (
                                    <>
                                        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                        Creating...
                                    </>
                                ) : (
                                    "Create Receipt"
                                )}
                            </Button>
                        </form>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
