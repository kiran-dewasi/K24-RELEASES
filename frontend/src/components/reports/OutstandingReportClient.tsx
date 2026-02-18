"use client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import MagicInput from "@/components/MagicInput";

interface Bill {
    date: string;
    party_name: string;
    bill_name: string;
    amount: number;
    due_date: string;
}

export default function OutstandingReportClient() {
    const [bills, setBills] = useState<Bill[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchBills = async () => {
            try {
                const headers: Record<string, string> = { "x-api-key": "k24-secret-key-123" };
                const token = localStorage.getItem("k24_token");
                if (token) headers["Authorization"] = `Bearer ${token}`;

                const res = await fetch(`${API_URL}/reports/outstanding`, {
                    headers: headers
                });
                const data = await res.json();
                setBills(data.bills || []);
            } catch (error) {
                console.error("Failed to fetch bills", error);
            } finally {
                setLoading(false);
            }
        };
        fetchBills();
    }, []);

    const totalOutstanding = bills.reduce((sum, b) => sum + b.amount, 0);

    return (
        <div className="p-8 space-y-6 pb-24">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Outstanding Receivables</h1>
                    <p className="text-muted-foreground">Bills pending collection</p>
                </div>
                <div className="text-right">
                    <p className="text-sm text-muted-foreground">Total Pending</p>
                    <p className="text-2xl font-bold text-red-600">₹{(totalOutstanding ?? 0).toLocaleString('en-IN')}</p>
                </div>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Pending Bills</CardTitle>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <p>Loading...</p>
                    ) : bills.length === 0 ? (
                        <p className="text-muted-foreground">No outstanding receivables. Once you create invoices, they'll appear here.</p>
                    ) : (
                        <div className="space-y-4">
                            {bills.map((b, idx) => (
                                <div key={idx} className="flex justify-between items-center border-b pb-2 last:border-0">
                                    <div>
                                        <p className="font-medium">{b.party_name}</p>
                                        <p className="text-sm text-muted-foreground">Bill #{b.bill_name} • Due: {b.due_date}</p>
                                    </div>
                                    <div className="font-bold">
                                        ₹{(b.amount ?? 0).toLocaleString('en-IN')}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>

            <div className="fixed bottom-6 right-6 w-96 z-50">
                <MagicInput
                    isFullPage={false}
                    allowEmbedded={true}
                    pageContext={{
                        page: "outstanding_report",
                        total_outstanding: totalOutstanding,
                        bill_count: bills.length
                    }}
                />
            </div>
        </div>
    );
}
