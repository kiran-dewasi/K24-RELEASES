"use client";

import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Cloud, Pen, Trash2, Printer, Clock } from "lucide-react";

interface Voucher {
    date: string;
    voucher_type: string;
    voucher_number: string;
    party_name: string;
    amount: number;
    narration: string;
    guid?: string;
}

interface VoucherDrawerProps {
    open: boolean;
    onClose: () => void;
    voucher: Voucher | null;
}

export function VoucherDrawer({ open, onClose, voucher }: VoucherDrawerProps) {
    if (!voucher) return null;

    return (
        <Sheet open={open} onOpenChange={onClose}>
            <SheetContent className="w-full sm:max-w-xl p-0 flex flex-col bg-slate-50">
                {/* Header */}
                <SheetHeader className="p-6 bg-white border-b">
                    <div className="flex items-start justify-between">
                        <div>
                            <Badge variant="outline" className="mb-2 bg-slate-100 text-slate-700 border-slate-200">
                                {voucher.voucher_type}
                            </Badge>
                            <SheetTitle className="text-xl">{voucher.party_name}</SheetTitle>
                            <SheetDescription>
                                Voucher #{voucher.voucher_number} • {voucher.date}
                            </SheetDescription>
                        </div>
                        <div className="text-right">
                            <div className="text-2xl font-bold tracking-tight">
                                ₹{Number(voucher.amount).toLocaleString('en-IN')}
                            </div>
                            <div className="flex items-center justify-end gap-1.5 mt-1 text-xs text-emerald-600 font-medium">
                                <Cloud className="h-3 w-3" /> Synced to Tally
                            </div>
                        </div>
                    </div>
                </SheetHeader>

                {/* Main Content */}
                <ScrollArea className="flex-1 p-6">
                    <div className="space-y-8">

                        {/* Narration */}
                        {voucher.narration && (
                            <div className="bg-white p-4 rounded-lg border shadow-sm">
                                <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">Narration</h4>
                                <p className="text-sm italic text-foreground/80 leading-relaxed">"{voucher.narration}"</p>
                            </div>
                        )}

                        {/* Line Items (Mock) - Commented out as per user request (Misleading Mock Data) */}
                        {/* 
                        <div className="space-y-3">
                            <h4 className="text-xs font-semibold uppercase text-muted-foreground px-1">Line Items</h4>
                            <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
                                <table className="w-full text-sm">
                                    <thead className="bg-muted/30 text-xs font-medium text-muted-foreground text-left">
                                        <tr>
                                            <th className="px-4 py-2">Particular</th>
                                            <th className="px-4 py-2 text-right">Amount</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y">
                                        <tr>
                                            <td className="px-4 py-3">
                                                <span className="font-medium text-foreground">Services Rendered</span>
                                                <br />
                                                <span className="text-xs text-muted-foreground">Software Development Charges</span>
                                            </td>
                                            <td className="px-4 py-3 text-right font-medium">₹{voucher.amount.toLocaleString('en-IN')}</td>
                                        </tr>
                                        <tr className="bg-slate-50/50">
                                            <td className="px-4 py-2 text-xs text-muted-foreground pl-8">IGST 18%</td>
                                            <td className="px-4 py-2 text-right text-xs text-muted-foreground">₹{(voucher.amount * 0.18).toLocaleString('en-IN')}</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        */}

                        {/* Audit Trail */}
                        <div className="space-y-3">
                            <h4 className="text-xs font-semibold uppercase text-muted-foreground px-1">Audit Trail</h4>
                            <div className="relative pl-4 border-l-2 border-muted space-y-6">
                                <div className="relative">
                                    <div className="absolute -left-[21px] top-1 h-3 w-3 rounded-full bg-emerald-500 ring-4 ring-white" />
                                    <p className="text-sm font-medium">Synced Successfully</p>
                                    <p className="text-xs text-muted-foreground flex items-center gap-1">
                                        <Clock className="h-3 w-3" /> 10 mins ago via Tally Connector
                                    </p>
                                </div>
                                <div className="relative">
                                    <div className="absolute -left-[21px] top-1 h-3 w-3 rounded-full bg-muted-foreground/30 ring-4 ring-white" />
                                    <p className="text-sm font-medium">Created by Kiran</p>
                                    <p className="text-xs text-muted-foreground flex items-center gap-1">
                                        <Clock className="h-3 w-3" /> 2 hours ago from Web
                                    </p>
                                </div>
                            </div>
                        </div>

                    </div>
                </ScrollArea>

                {/* Footer Actions */}
                <SheetFooter className="p-4 bg-white border-t sm:justify-between items-center">
                    <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive hover:bg-destructive/10 gap-2">
                        <Trash2 className="h-4 w-4" /> Delete
                    </Button>
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" className="gap-2">
                            <Printer className="h-4 w-4" /> Print
                        </Button>
                        <Button size="sm" className="gap-2">
                            <Pen className="h-4 w-4" /> Edit Voucher
                        </Button>
                    </div>
                </SheetFooter>
            </SheetContent>
        </Sheet>
    );
}
