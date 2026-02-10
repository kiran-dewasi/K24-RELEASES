"use client";

import { useState, useEffect } from "react";
import { API_CONFIG } from "@/lib/api-config";

import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MoreVertical, CheckCircle2, AlertCircle, Clock, FileCheck } from "lucide-react";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface Transaction {
    id: string;
    date: string;
    type: "Invoice" | "Receipt" | "Payment" | "Sales";
    voucher_no: string;
    party: string;
    amount: number;
    status: "Paid" | "Unpaid" | "Overdue" | "Draft";
    gst_compliant: boolean;
    synced: boolean;
}

export function InvoicesTable() {
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchInvoices = async () => {
            try {
                // Fetching all vouchers for now, can filter by ?type=Sales if needed
                const res = await fetch(`${API_CONFIG.BASE_URL}/vouchers`, {
                    headers: { "x-api-key": "k24-secret-key-123" }
                });
                const data = await res.json();

                const vouchers = (data.vouchers || []).map((v: any) => ({
                    id: v.id || Math.random().toString(),
                    date: v.date,
                    type: v.voucher_type as any,
                    voucher_no: v.voucher_number || "PENDING",
                    party: v.party_name,
                    amount: v.amount,
                    status: "Paid", // TODO: Fetch real status from outstanding bills logic
                    gst_compliant: true, // Placeholder for now
                    synced: v.sync_status === "SYNCED"
                }));

                setTransactions(vouchers);
            } catch (err) {
                console.error("Failed to load invoices", err);
            } finally {
                setLoading(false);
            }
        };

        fetchInvoices();
    }, []);

    if (loading) {
        return <div className="p-8 text-center text-muted-foreground">Loading transactions...</div>;
    }

    if (transactions.length === 0) {
        return <div className="p-8 text-center text-muted-foreground">No recent transactions found.</div>;
    }

    return (
        <div className="rounded-md border bg-white shadow-sm overflow-hidden">
            <Table>
                <TableHeader className="bg-muted/50">
                    <TableRow>
                        <TableHead className="w-[120px]">Date</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Party</TableHead>
                        <TableHead>Voucher No</TableHead>
                        <TableHead className="text-right">Amount</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-center">GST</TableHead>
                        <TableHead className="text-center">Sync</TableHead>
                        <TableHead className="w-[50px]"></TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {transactions.map((t) => (
                        <TableRow key={t.id} className="group hover:bg-muted/50 cursor-pointer transition-colors">
                            <TableCell className="font-medium text-muted-foreground whitespace-nowrap">
                                {t.date}
                            </TableCell>
                            <TableCell>
                                <Badge variant="outline" className={`
                                    ${t.type === 'Invoice' ? 'border-blue-200 text-blue-700 bg-blue-50' : ''}
                                    ${t.type === 'Sales' ? 'border-blue-200 text-blue-700 bg-blue-50' : ''}
                                    ${t.type === 'Receipt' ? 'border-green-200 text-green-700 bg-green-50' : ''}
                                    ${t.type === 'Payment' ? 'border-orange-200 text-orange-700 bg-orange-50' : ''}
                                `}>
                                    {t.type}
                                </Badge>
                            </TableCell>
                            <TableCell className="font-medium">{t.party}</TableCell>
                            <TableCell className="font-mono text-xs text-muted-foreground">{t.voucher_no}</TableCell>
                            <TableCell className="text-right font-semibold">
                                ₹{t.amount.toLocaleString('en-IN')}
                            </TableCell>
                            <TableCell>
                                <StatusBadge status={t.status} />
                            </TableCell>
                            <TableCell className="text-center">
                                {t.gst_compliant ? (
                                    <FileCheck className="h-4 w-4 text-emerald-500 mx-auto" />
                                ) : (
                                    <span className="text-xs text-muted-foreground">-</span>
                                )}
                            </TableCell>
                            <TableCell className="text-center">
                                {t.synced ? (
                                    <CheckCircle2 className="h-4 w-4 text-emerald-500 mx-auto" />
                                ) : (
                                    <AlertCircle className="h-4 w-4 text-amber-500 mx-auto" />
                                )}
                            </TableCell>
                            <TableCell>
                                <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                        <Button variant="ghost" className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <span className="sr-only">Open menu</span>
                                            <MoreVertical className="h-4 w-4" />
                                        </Button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="end">
                                        <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                        <DropdownMenuItem>View Details</DropdownMenuItem>
                                        <DropdownMenuItem>Generate PDF</DropdownMenuItem>
                                        <DropdownMenuSeparator />
                                        <DropdownMenuItem>Retry Sync</DropdownMenuItem>
                                    </DropdownMenuContent>
                                </DropdownMenu>
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </div>
    );
}

function StatusBadge({ status }: { status: string }) {
    switch (status) {
        case "Paid":
            return <Badge variant="secondary" className="bg-emerald-100 text-emerald-800 hover:bg-emerald-100 border-none">Paid</Badge>;
        case "Overdue":
            return <Badge variant="destructive" className="bg-red-100 text-red-800 hover:bg-red-100 border-none">Overdue</Badge>;
        case "Unpaid":
            return <Badge variant="outline" className="text-amber-700 bg-amber-50 border-amber-200">Unpaid</Badge>;
        default:
            return <Badge variant="outline">{status}</Badge>;
    }
}
