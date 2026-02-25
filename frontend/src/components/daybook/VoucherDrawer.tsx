"use client";

import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Cloud, Pen, Trash2, Printer, Package, Receipt, IndianRupee, AlertCircle } from "lucide-react";

interface Voucher {
    date: string;
    voucher_type: string;
    voucher_number: string;
    party_name: string;
    amount: number | string;
    narration: string;
    guid?: string;
    ledger_id?: number | string;
}

interface LineItem {
    name: string;
    quantity: number;
    rate: number;
    amount: number;
    godown?: string;
    batch?: string;
}

interface LedgerEntry {
    name: string;
    amount: number;
    is_tax: boolean;
}

interface VoucherDetail {
    voucher_number?: string;
    date?: string;
    voucher_type?: string;
    party_name?: string;
    narration?: string;
    guid?: string;
    items?: LineItem[];
    ledgers?: LedgerEntry[];
    tax_breakdown?: LedgerEntry[];
    total_amount?: number;
    source?: string;
}

interface VoucherDrawerProps {
    open: boolean;
    onClose: () => void;
    voucher: Voucher | null;
    detailData?: Record<string, unknown> | null;
    detailLoading?: boolean;
}

function formatCurrency(val: number | string | undefined): string {
    const n = typeof val === "string" ? parseFloat(val) : (val ?? 0);
    if (isNaN(n)) return "₹0.00";
    return `₹${Math.abs(n).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function getTaxLabel(name: string): string {
    const upper = name.toUpperCase();
    if (upper.includes("IGST")) return "IGST";
    if (upper.includes("CGST")) return "CGST";
    if (upper.includes("SGST")) return "SGST";
    if (upper.includes("CESS")) return "Cess";
    if (upper.includes("GST")) return "GST";
    if (upper.includes("TAX")) return "Tax";
    return name;
}

function getBadgeColor(vtype: string): string {
    const t = vtype.toLowerCase();
    if (t.includes("purchase")) return "bg-orange-100 text-orange-700 border-orange-200";
    if (t.includes("sales") || t.includes("sale")) return "bg-blue-100 text-blue-700 border-blue-200";
    if (t.includes("receipt")) return "bg-emerald-100 text-emerald-700 border-emerald-200";
    if (t.includes("payment")) return "bg-rose-100 text-rose-700 border-rose-200";
    if (t.includes("journal")) return "bg-purple-100 text-purple-700 border-purple-200";
    return "bg-slate-100 text-slate-700 border-slate-200";
}

function LoadingSkeleton() {
    return (
        <div className="space-y-4 animate-pulse p-2">
            <div className="h-4 bg-slate-200 rounded w-3/4" />
            <div className="h-4 bg-slate-200 rounded w-1/2" />
            <div className="h-32 bg-slate-100 rounded-lg" />
            <div className="h-4 bg-slate-200 rounded w-2/3" />
            <div className="h-24 bg-slate-100 rounded-lg" />
        </div>
    );
}

export function VoucherDrawer({ open, onClose, voucher, detailData, detailLoading }: VoucherDrawerProps) {
    if (!voucher) return null;

    const detail = detailData as VoucherDetail | null;
    const items: LineItem[] = (detail?.items as LineItem[]) ?? [];
    const ledgers: LedgerEntry[] = (detail?.ledgers as LedgerEntry[]) ?? [];
    const taxEntries: LedgerEntry[] = (detail?.tax_breakdown as LedgerEntry[]) ?? [];

    // Non-party, non-tax ledgers (Hamali, Transport, Cash, Bank, etc.)
    const otherLedgers = ledgers.filter(l => !l.is_tax);
    const fromTally = detail?.source === "tally";

    const displayAmount = detail?.total_amount ?? Number(voucher.amount);
    const narration = detail?.narration || voucher.narration;

    return (
        <Sheet open={open} onOpenChange={onClose}>
            <SheetContent className="w-full sm:max-w-xl p-0 flex flex-col bg-slate-50">

                {/* ── Header ─────────────────────────────────── */}
                <SheetHeader className="p-6 bg-white border-b">
                    <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                            <Badge variant="outline" className={`mb-2 text-xs font-medium border ${getBadgeColor(voucher.voucher_type)}`}>
                                {voucher.voucher_type}
                            </Badge>
                            <SheetTitle className="text-lg leading-tight truncate">{voucher.party_name}</SheetTitle>
                            <SheetDescription className="text-xs mt-0.5">
                                #{voucher.voucher_number} &bull; {voucher.date}
                                {fromTally && (
                                    <span className="ml-2 inline-flex items-center gap-1 text-emerald-600 font-medium">
                                        <Cloud className="h-3 w-3" /> Live Tally
                                    </span>
                                )}
                            </SheetDescription>
                        </div>
                        <div className="text-right shrink-0">
                            <div className="text-xl font-bold tracking-tight text-slate-800">
                                {formatCurrency(displayAmount)}
                            </div>
                        </div>
                    </div>
                </SheetHeader>

                {/* ── Body ───────────────────────────────────── */}
                <ScrollArea className="flex-1">
                    <div className="p-5 space-y-5">

                        {/* Loading State */}
                        {detailLoading && <LoadingSkeleton />}

                        {/* Error / No Tally connection */}
                        {!detailLoading && !detail && (
                            <div className="flex items-center gap-2 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3">
                                <AlertCircle className="h-4 w-4 shrink-0" />
                                <span>Could not fetch live details from Tally. Showing available info only.</span>
                            </div>
                        )}

                        {/* ── Narration ── */}
                        {narration && (
                            <div className="bg-white p-4 rounded-lg border shadow-sm">
                                <p className="text-xs font-semibold uppercase text-muted-foreground mb-1.5">Narration</p>
                                <p className="text-sm italic text-foreground/75 leading-relaxed">"{narration}"</p>
                            </div>
                        )}

                        {/* ── Stock Items Table ── */}
                        {!detailLoading && items.length > 0 && (
                            <div className="space-y-2">
                                <div className="flex items-center gap-2 px-1">
                                    <Package className="h-4 w-4 text-muted-foreground" />
                                    <h4 className="text-xs font-semibold uppercase text-muted-foreground">Items / Stock</h4>
                                </div>
                                <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
                                    <table className="w-full text-sm">
                                        <thead className="bg-slate-50 text-xs font-medium text-muted-foreground text-left border-b">
                                            <tr>
                                                <th className="px-4 py-2.5">Item</th>
                                                <th className="px-3 py-2.5 text-right">Qty</th>
                                                <th className="px-3 py-2.5 text-right">Rate</th>
                                                <th className="px-3 py-2.5 text-right">Amount</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y">
                                            {items.map((item, i) => (
                                                <tr key={i} className="hover:bg-slate-50/50 transition-colors">
                                                    <td className="px-4 py-3">
                                                        <span className="font-medium text-foreground">{item.name}</span>
                                                        {item.godown && item.godown !== "Main Location" && (
                                                            <span className="block text-xs text-muted-foreground mt-0.5">{item.godown}</span>
                                                        )}
                                                    </td>
                                                    <td className="px-3 py-3 text-right text-muted-foreground tabular-nums">
                                                        {item.quantity > 0 ? item.quantity.toFixed(2) : "—"}
                                                    </td>
                                                    <td className="px-3 py-3 text-right text-muted-foreground tabular-nums">
                                                        {item.rate > 0 ? formatCurrency(item.rate) : "—"}
                                                    </td>
                                                    <td className="px-3 py-3 text-right font-semibold tabular-nums">
                                                        {formatCurrency(item.amount)}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}

                        {/* ── Ledger / Accounts Table ── */}
                        {!detailLoading && otherLedgers.length > 0 && (
                            <div className="space-y-2">
                                <div className="flex items-center gap-2 px-1">
                                    <Receipt className="h-4 w-4 text-muted-foreground" />
                                    <h4 className="text-xs font-semibold uppercase text-muted-foreground">Account Entries</h4>
                                </div>
                                <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
                                    <table className="w-full text-sm">
                                        <tbody className="divide-y">
                                            {otherLedgers.map((led, i) => {
                                                const isCredit = led.amount > 0;
                                                return (
                                                    <tr key={i} className="hover:bg-slate-50/50 transition-colors">
                                                        <td className="px-4 py-3">
                                                            <span className="font-medium text-foreground">{led.name}</span>
                                                        </td>
                                                        <td className="px-4 py-3 text-right">
                                                            <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${isCredit ? "bg-rose-50 text-rose-600" : "bg-emerald-50 text-emerald-600"}`}>
                                                                {isCredit ? "Cr" : "Dr"}
                                                            </span>
                                                        </td>
                                                        <td className="px-4 py-3 text-right font-semibold tabular-nums">
                                                            {formatCurrency(Math.abs(led.amount))}
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}

                        {/* ── Tax Breakdown ── */}
                        {!detailLoading && taxEntries.length > 0 && (
                            <div className="space-y-2">
                                <div className="flex items-center gap-2 px-1">
                                    <IndianRupee className="h-4 w-4 text-muted-foreground" />
                                    <h4 className="text-xs font-semibold uppercase text-muted-foreground">Tax Breakdown</h4>
                                </div>
                                <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
                                    <table className="w-full text-sm">
                                        <tbody className="divide-y">
                                            {taxEntries.map((tax, i) => (
                                                <tr key={i} className="hover:bg-slate-50/50 transition-colors">
                                                    <td className="px-4 py-2.5">
                                                        <span className="text-muted-foreground">{tax.name}</span>
                                                    </td>
                                                    <td className="px-4 py-2.5 text-right">
                                                        <Badge variant="outline" className="text-xs text-amber-700 border-amber-200 bg-amber-50">
                                                            {getTaxLabel(tax.name)}
                                                        </Badge>
                                                    </td>
                                                    <td className="px-4 py-2.5 text-right font-semibold tabular-nums">
                                                        {formatCurrency(Math.abs(tax.amount))}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                        {taxEntries.length > 1 && (
                                            <tfoot className="bg-slate-50 border-t">
                                                <tr>
                                                    <td colSpan={2} className="px-4 py-2 text-xs font-semibold text-muted-foreground uppercase">Total Tax</td>
                                                    <td className="px-4 py-2 text-right font-bold tabular-nums">
                                                        {formatCurrency(taxEntries.reduce((s, t) => s + Math.abs(t.amount), 0))}
                                                    </td>
                                                </tr>
                                            </tfoot>
                                        )}
                                    </table>
                                </div>
                            </div>
                        )}

                        {/* ── Grand Total Summary ── */}
                        {!detailLoading && detail && (
                            <>
                                <Separator />
                                <div className="flex items-center justify-between px-1">
                                    <span className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Grand Total</span>
                                    <span className="text-xl font-bold text-slate-900 tabular-nums">
                                        {formatCurrency(displayAmount)}
                                    </span>
                                </div>
                            </>
                        )}

                        {/* ── No detail at all ── */}
                        {!detailLoading && !detail && !narration && (
                            <div className="text-center text-sm text-muted-foreground py-8">
                                No additional details available for this voucher.
                            </div>
                        )}

                    </div>
                </ScrollArea>

                {/* ── Footer Actions ─────────────────────────── */}
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
