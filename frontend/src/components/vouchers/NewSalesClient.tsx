"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Plus, Trash2, Loader2 } from "lucide-react";
import { API_CONFIG } from "@/lib/api-config";
import { LedgerAutocomplete } from "@/components/ui/ledger-autocomplete";

interface LineItem {
    id: string;
    description: string;
    quantity: number;
    rate: number;
    amount: number;
}

interface SelectedLedger {
    id: number;
    name: string;
    group?: string;
    gstin?: string;
}

export default function NewSalesClient() {
    const router = useRouter();

    // Form State
    const [partyName, setPartyName] = useState("");
    const [selectedLedger, setSelectedLedger] = useState<SelectedLedger | null>(null);
    const [invoiceNumber, setInvoiceNumber] = useState("");
    const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
    const [lineItems, setLineItems] = useState<LineItem[]>([
        { id: "1", description: "", quantity: 1, rate: 0, amount: 0 }
    ]);
    const [gstRate, setGstRate] = useState(18); // Default 18% GST
    const [discount, setDiscount] = useState(0);
    const [narration, setNarration] = useState("");

    // UI State
    const [loading, setLoading] = useState(false);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);

    // Calculations
    const subtotal = lineItems.reduce((sum, item) => sum + item.amount, 0);
    const discountAmount = (subtotal * discount) / 100;
    const taxableAmount = subtotal - discountAmount;
    const gstAmount = (taxableAmount * gstRate) / 100;
    const grandTotal = taxableAmount + gstAmount;

    // Handle ledger selection from autocomplete
    const handleLedgerSelect = (ledger: SelectedLedger | null) => {
        setSelectedLedger(ledger);
        // Could pre-fill GST info or other details based on ledger selection
        console.log("Selected ledger:", ledger);
    };

    const addLineItem = () => {
        const newItem: LineItem = {
            id: Date.now().toString(),
            description: "",
            quantity: 1,
            rate: 0,
            amount: 0
        };
        setLineItems([...lineItems, newItem]);
    };

    const removeLineItem = (id: string) => {
        if (lineItems.length > 1) {
            setLineItems(lineItems.filter(item => item.id !== id));
        }
    };

    const updateLineItem = (id: string, field: keyof LineItem, value: any) => {
        setLineItems(lineItems.map(item => {
            if (item.id === id) {
                const updated = { ...item, [field]: value };
                // Recalculate amount
                if (field === 'quantity' || field === 'rate') {
                    updated.amount = updated.quantity * updated.rate;
                }
                return updated;
            }
            return item;
        }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setErrorMsg(null);

        try {
            const res = await fetch(`${API_CONFIG.BASE_URL}/vouchers/sales`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "x-api-key": "k24-secret-key-123"
                },
                body: JSON.stringify({
                    party_name: partyName,
                    invoice_number: invoiceNumber,
                    date,
                    items: lineItems.map(item => ({
                        description: item.description,
                        quantity: item.quantity,
                        rate: item.rate,
                        amount: item.amount
                    })),
                    // Ensure numbers are numbers
                    subtotal: Number(subtotal),
                    discount_percent: Number(discount),
                    discount_amount: Number(discountAmount),
                    gst_rate: Number(gstRate),
                    gst_amount: Number(gstAmount),
                    grand_total: Number(grandTotal),
                    narration
                })
            });

            // Handle non-JSON responses gracefully
            const contentType = res.headers.get("content-type");
            let data;
            if (contentType && contentType.includes("application/json")) {
                data = await res.json();
            } else {
                data = { detail: await res.text() };
            }

            if (res.ok) {
                alert("Sales Invoice created successfully!");
                router.push("/daybook");
            } else {
                setErrorMsg(data.detail || "Failed to create invoice in Tally");
                console.error("API Error:", data);
            }
        } catch (error: any) {
            console.error("Failed to create invoice", error);
            setErrorMsg(error.message || "Network Error: Failed to connect to backend.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 p-8">
            <div className="max-w-5xl mx-auto space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Button variant="ghost" size="icon" onClick={() => router.back()}>
                            <ArrowLeft className="h-5 w-5" />
                        </Button>
                        <div>
                            <h1 className="text-3xl font-bold tracking-tight">New Sales Invoice</h1>
                            <p className="text-muted-foreground">Create professional invoices</p>
                        </div>
                    </div>
                    <div className="text-right">
                        <p className="text-sm text-muted-foreground">Grand Total</p>
                        <p className="text-3xl font-bold text-blue-600">₹{grandTotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</p>
                    </div>
                </div>

                {/* Error Banner */}
                {errorMsg && (
                    <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
                        <strong className="font-bold">Error: </strong>
                        <span className="block sm:inline">{errorMsg}</span>
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-6">
                    {/* Invoice Details Card */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Invoice Details</CardTitle>
                        </CardHeader>
                        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {/* Party Name with Autocomplete */}
                            <div className="space-y-2 md:col-span-2">
                                <label className="text-sm font-medium">Customer/Party Name *</label>
                                <LedgerAutocomplete
                                    value={partyName}
                                    onChange={setPartyName}
                                    onSelect={handleLedgerSelect}
                                    placeholder="e.g. ABC Traders (type to search or create new)"
                                    ledgerType="customer"
                                    showBalance={true}
                                />
                                {selectedLedger && selectedLedger.gstin && (
                                    <p className="text-xs text-green-600">
                                        ✓ GSTIN: {selectedLedger.gstin}
                                    </p>
                                )}
                                {partyName && !selectedLedger && (
                                    <p className="text-xs text-blue-500">
                                        💡 New ledger will be auto-created on save
                                    </p>
                                )}
                            </div>

                            {/* Invoice Number */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Invoice Number</label>
                                <input
                                    type="text"
                                    placeholder="Auto-generated"
                                    value={invoiceNumber}
                                    onChange={(e) => setInvoiceNumber(e.target.value)}
                                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                />
                            </div>

                            {/* Date */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Date *</label>
                                <input
                                    type="date"
                                    value={date}
                                    onChange={(e) => setDate(e.target.value)}
                                    required
                                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                />
                            </div>
                        </CardContent>
                    </Card>

                    {/* Line Items Card */}
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <CardTitle>Items</CardTitle>
                            <Button type="button" onClick={addLineItem} size="sm" className="bg-green-600 hover:bg-green-700">
                                <Plus className="h-4 w-4 mr-2" />
                                Add Item
                            </Button>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {/* Header Row */}
                                <div className="grid grid-cols-12 gap-4 font-semibold text-sm text-gray-600 pb-2 border-b">
                                    <div className="col-span-5">Description</div>
                                    <div className="col-span-2">Quantity</div>
                                    <div className="col-span-2">Rate (₹)</div>
                                    <div className="col-span-2">Amount (₹)</div>
                                    <div className="col-span-1"></div>
                                </div>

                                {/* Line Items */}
                                {lineItems.map((item, index) => (
                                    <div key={item.id} className="grid grid-cols-12 gap-4 items-center">
                                        <div className="col-span-5">
                                            <input
                                                type="text"
                                                placeholder="Item description"
                                                value={item.description}
                                                onChange={(e) => updateLineItem(item.id, 'description', e.target.value)}
                                                required
                                                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            />
                                        </div>
                                        <div className="col-span-2">
                                            <input
                                                type="number"
                                                min="0"
                                                step="0.01"
                                                value={item.quantity}
                                                onChange={(e) => updateLineItem(item.id, 'quantity', parseFloat(e.target.value) || 0)}
                                                required
                                                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            />
                                        </div>
                                        <div className="col-span-2">
                                            <input
                                                type="number"
                                                min="0"
                                                step="0.01"
                                                value={item.rate}
                                                onChange={(e) => updateLineItem(item.id, 'rate', parseFloat(e.target.value) || 0)}
                                                required
                                                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            />
                                        </div>
                                        <div className="col-span-2">
                                            <div className="px-3 py-2 bg-gray-50 rounded-lg font-medium">
                                                {item.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                                            </div>
                                        </div>
                                        <div className="col-span-1">
                                            <Button
                                                type="button"
                                                variant="ghost"
                                                size="icon"
                                                onClick={() => removeLineItem(item.id)}
                                                disabled={lineItems.length === 1}
                                                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Calculations Card */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Calculation Summary</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    {/* Left: Discount & GST */}
                                    <div className="space-y-4">
                                        <div className="space-y-2">
                                            <label className="text-sm font-medium">Discount (%)</label>
                                            <input
                                                type="number"
                                                min="0"
                                                max="100"
                                                step="0.01"
                                                value={discount}
                                                onChange={(e) => setDiscount(parseFloat(e.target.value) || 0)}
                                                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-sm font-medium">GST Rate (%)</label>
                                            <select
                                                value={gstRate}
                                                onChange={(e) => setGstRate(parseFloat(e.target.value))}
                                                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
                                            >
                                                <option value="0">0% (No GST)</option>
                                                <option value="5">5%</option>
                                                <option value="12">12%</option>
                                                <option value="18">18%</option>
                                                <option value={28}>28%</option>
                                            </select>
                                        </div>
                                    </div>

                                    {/* Right: Totals */}
                                    <div className="space-y-3 bg-gray-50 p-4 rounded-lg">
                                        <div className="flex justify-between text-sm">
                                            <span className="text-gray-600">Subtotal:</span>
                                            <span className="font-medium">₹{subtotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                                        </div>
                                        {discount > 0 && (
                                            <div className="flex justify-between text-sm">
                                                <span className="text-gray-600">Discount ({discount}%):</span>
                                                <span className="font-medium text-red-600">-₹{discountAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                                            </div>
                                        )}
                                        <div className="flex justify-between text-sm">
                                            <span className="text-gray-600">Taxable Amount:</span>
                                            <span className="font-medium">₹{taxableAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                                        </div>
                                        {gstRate > 0 && (
                                            <div className="flex justify-between text-sm">
                                                <span className="text-gray-600">GST ({gstRate}%):</span>
                                                <span className="font-medium">₹{gstAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                                            </div>
                                        )}
                                        <div className="pt-3 border-t border-gray-300 flex justify-between text-lg">
                                            <span className="font-semibold">Grand Total:</span>
                                            <span className="font-bold text-blue-600">₹{grandTotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                                        </div>
                                    </div>
                                </div>

                                {/* Narration */}
                                <div className="space-y-2">
                                    <label className="text-sm font-medium">Narration/Notes</label>
                                    <textarea
                                        placeholder="Additional notes..."
                                        value={narration}
                                        onChange={(e) => setNarration(e.target.value)}
                                        rows={3}
                                        className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                                    />
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Submit Button */}
                    <div className="flex gap-4">
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => router.back()}
                            className="flex-1"
                        >
                            Cancel
                        </Button>
                        <Button
                            type="submit"
                            disabled={loading}
                            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-6 text-lg font-medium"
                        >
                            {loading ? (
                                <>
                                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                    Creating...
                                </>
                            ) : (
                                "Create Invoice & Save to Tally"
                            )}
                        </Button>
                    </div>
                </form>
            </div>
        </div>
    );
}
