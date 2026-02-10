"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, DollarSign, Check, AlertCircle } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";

interface OutstandingBill {
    bill_name: string;
    party_name: string;
    amount: number;
    due_date?: string;
}

export default function PremiumReceiptPage() {
    const router = useRouter();
    const [partyQuery, setPartyQuery] = useState("");
    const [partySuggestions, setPartySuggestions] = useState<string[]>([]);
    const [formData, setFormData] = useState({
        party_name: "",
        amount: "",
        deposit_to: "Cash",
        payment_method: "Cash",
        reference: "",
        narration: "",
        date: new Date().toISOString().split("T")[0]
    });

    const [outstandingBills, setOutstandingBills] = useState<OutstandingBill[]>([]);
    const [selectedBills, setSelectedBills] = useState<Set<string>>(new Set());
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState("");

    // Fetch party suggestions
    useEffect(() => {
        if (partyQuery.length < 2) {
            setPartySuggestions([]);
            return;
        }

        const timer = setTimeout(async () => {
            try {
                const res = await fetch(`http://localhost:8000/ledgers/search?query=${partyQuery}`, {
                    headers: { "x-api-key": "k24-secret-key-123" }
                });
                const data = await res.json();
                setPartySuggestions(data.matches || []);
            } catch (err) {
                console.error("Failed to fetch suggestions", err);
            }
        }, 300);

        return () => clearTimeout(timer);
    }, [partyQuery]);

    // Fetch outstanding bills when party is selected
    useEffect(() => {
        if (!formData.party_name) {
            setOutstandingBills([]);
            return;
        }

        const fetchOutstanding = async () => {
            try {
                const res = await fetch(`http://localhost:8000/bills/receivables`, {
                    headers: { "x-api-key": "k24-secret-key-123" }
                });
                const data = await res.json();

                // Filter for this party
                const partyBills = data.filter((b: OutstandingBill) =>
                    b.party_name?.toLowerCase() === formData.party_name.toLowerCase()
                );
                setOutstandingBills(partyBills);
            } catch (err) {
                console.error("Failed to fetch outstanding bills", err);
            }
        };

        fetchOutstanding();
    }, [formData.party_name]);

    const handleSelectParty = (party: string) => {
        setFormData({ ...formData, party_name: party });
        setPartyQuery(party);
        setPartySuggestions([]);
    };

    const toggleBill = (billName: string, amount: number) => {
        const newSelected = new Set(selectedBills);
        if (newSelected.has(billName)) {
            newSelected.delete(billName);
        } else {
            newSelected.add(billName);
        }
        setSelectedBills(newSelected);

        // Auto-calculate total amount
        const total = outstandingBills
            .filter(b => newSelected.has(b.bill_name))
            .reduce((sum, b) => sum + b.amount, 0);

        setFormData({ ...formData, amount: total.toString() });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitting(true);
        setError("");

        const finalPartyName = formData.party_name || partyQuery;

        try {
            const res = await fetch("http://localhost:8000/operations/receipt", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "x-api-key": "k24-secret-key-123"
                },
                body: JSON.stringify({
                    ...formData,
                    party_name: finalPartyName,
                    amount: parseFloat(formData.amount),
                    bank_cash_ledger: formData.deposit_to,
                    settled_bills: Array.from(selectedBills)
                })
            });

            const data = await res.json();

            if (res.ok) {
                alert(`✅ Receipt created for ₹${formData.amount}`);
                router.push("/daybook");
            } else {
                setError(data.detail || "Failed to create receipt");
            }
        } catch (err) {
            setError("Network error. Please try again.");
        } finally {
            setSubmitting(false);
        }
    };

    const totalOutstanding = outstandingBills.reduce((sum, b) => sum + b.amount, 0);
    const selectedAmount = outstandingBills
        .filter(b => selectedBills.has(b.bill_name))
        .reduce((sum, b) => sum + b.amount, 0);

    return (
        <div className="min-h-screen bg-gray-50 p-8">
            <div className="max-w-4xl mx-auto space-y-6">
                {/* Header */}
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" onClick={() => router.back()}>
                        <ArrowLeft className="h-5 w-5" />
                    </Button>
                    <div>
                        <h1 className="text-3xl font-bold">Premium Receipt</h1>
                        <p className="text-muted-foreground">Smart bill settlement & multi-method support</p>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Receipt Form */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Receipt Details</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <form onSubmit={handleSubmit} className="space-y-4">
                                {/* Party Selection */}
                                <div>
                                    <Label>Customer Name</Label>
                                    <Input
                                        value={partyQuery}
                                        onChange={(e) => {
                                            setPartyQuery(e.target.value);
                                            setFormData({ ...formData, party_name: "" });
                                        }}
                                        placeholder="Type customer name..."
                                        required
                                    />
                                    {partySuggestions.length > 0 && (
                                        <div className="mt-1 border rounded-md shadow-lg bg-white max-h-48 overflow-y-auto">
                                            {partySuggestions.map((party, idx) => (
                                                <div
                                                    key={idx}
                                                    className="px-4 py-2 hover:bg-blue-50 cursor-pointer"
                                                    onClick={() => handleSelectParty(party)}
                                                >
                                                    {party}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                    {formData.party_name && (
                                        <Badge className="mt-2 bg-green-100 text-green-800">
                                            <Check className="h-3 w-3 mr-1" /> {formData.party_name}
                                        </Badge>
                                    )}
                                </div>

                                {/* Date */}
                                <div>
                                    <Label>Date</Label>
                                    <Input
                                        type="date"
                                        value={formData.date}
                                        onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                                        required
                                    />
                                </div>

                                {/* Payment Method */}
                                <div>
                                    <Label>Payment Method</Label>
                                    <select
                                        className="w-full border rounded-md p-2"
                                        value={formData.payment_method}
                                        onChange={(e) => setFormData({ ...formData, payment_method: e.target.value })}
                                    >
                                        <option value="Cash">Cash</option>
                                        <option value="Bank Transfer">Bank Transfer</option>
                                        <option value="UPI">UPI</option>
                                        <option value="Cheque">Cheque</option>
                                        <option value="Card">Card</option>
                                    </select>
                                </div>

                                {/* Reference Number (for non-cash) */}
                                {formData.payment_method !== "Cash" && (
                                    <div>
                                        <Label>Reference Number</Label>
                                        <Input
                                            value={formData.reference}
                                            onChange={(e) => setFormData({ ...formData, reference: e.target.value })}
                                            placeholder="Txn ID / Cheque No."
                                        />
                                    </div>
                                )}

                                {/* Amount */}
                                <div>
                                    <Label>Amount Received</Label>
                                    <Input
                                        type="number"
                                        step="0.01"
                                        value={formData.amount}
                                        onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                                        placeholder="0.00"
                                        required
                                    />
                                    {selectedAmount > 0 && (
                                        <p className="text-xs text-green-600 mt-1">
                                            Auto-filled: ₹{selectedAmount.toLocaleString('en-IN')} from selected bills
                                        </p>
                                    )}
                                </div>

                                {/* Deposit To */}
                                <div>
                                    <Label>Deposit To</Label>
                                    <select
                                        className="w-full border rounded-md p-2"
                                        value={formData.deposit_to}
                                        onChange={(e) => setFormData({ ...formData, deposit_to: e.target.value })}
                                    >
                                        <option value="Cash">Cash</option>
                                        <option value="Bank">Bank Account</option>
                                    </select>
                                </div>

                                {/* Narration */}
                                <div>
                                    <Label>Narration (Optional)</Label>
                                    <Input
                                        value={formData.narration}
                                        onChange={(e) => setFormData({ ...formData, narration: e.target.value })}
                                        placeholder="Additional notes..."
                                    />
                                </div>

                                {error && (
                                    <div className="flex items-center gap-2 text-red-600 text-sm">
                                        <AlertCircle className="h-4 w-4" />
                                        {error}
                                    </div>
                                )}

                                <Button type="submit" className="w-full" disabled={submitting || (!formData.party_name && !partyQuery)}>
                                    {submitting ? "Saving..." : "Save Receipt"}
                                </Button>
                            </form>
                        </CardContent>
                    </Card>

                    {/* Outstanding Bills Settlement */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <DollarSign className="h-5 w-5 text-green-600" />
                                Bill Settlement
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {!formData.party_name ? (
                                <p className="text-muted-foreground text-center py-8">
                                    Select a customer to see outstanding bills
                                </p>
                            ) : outstandingBills.length === 0 ? (
                                <div className="text-center py-8">
                                    <Check className="h-12 w-12 text-green-500 mx-auto mb-2" />
                                    <p className="font-medium text-green-700">No Outstanding Bills</p>
                                    <p className="text-sm text-muted-foreground">This customer has cleared all dues</p>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
                                        <p className="text-sm font-medium">Total Outstanding</p>
                                        <p className="text-2xl font-bold text-blue-700">
                                            ₹{totalOutstanding.toLocaleString('en-IN')}
                                        </p>
                                    </div>

                                    <p className="text-sm text-muted-foreground">
                                        Select bills to settle with this receipt:
                                    </p>

                                    <div className="space-y-2 max-h-80 overflow-y-auto">
                                        {outstandingBills.map((bill) => (
                                            <div
                                                key={bill.bill_name}
                                                className={`flex items-start gap-3 p-3 border rounded-md cursor-pointer transition-colors ${selectedBills.has(bill.bill_name)
                                                    ? 'bg-green-50 border-green-300'
                                                    : 'hover:bg-gray-50'
                                                    }`}
                                                onClick={() => toggleBill(bill.bill_name, bill.amount)}
                                            >
                                                <Checkbox
                                                    checked={selectedBills.has(bill.bill_name)}
                                                    onCheckedChange={() => toggleBill(bill.bill_name, bill.amount)}
                                                />
                                                <div className="flex-1">
                                                    <p className="font-medium">{bill.bill_name}</p>
                                                    <p className="text-sm text-muted-foreground">
                                                        ₹{bill.amount.toLocaleString('en-IN')}
                                                    </p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>

                                    {selectedBills.size > 0 && (
                                        <div className="bg-green-50 border border-green-200 rounded-md p-3">
                                            <p className="text-sm font-medium">Settling {selectedBills.size} bills</p>
                                            <p className="text-xl font-bold text-green-700">
                                                ₹{selectedAmount.toLocaleString('en-IN')}
                                            </p>
                                        </div>
                                    )}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
