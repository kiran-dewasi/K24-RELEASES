"use client";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MoreHorizontal, ArrowRight, ArrowLeft } from "lucide-react";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import { PaginationControls } from "@/components/ui/pagination-controls";

import Link from "next/link";

// ---------------------------------------------------------------------------
// Tally Voucher Debit / Credit Classification
// Rule: based on which side the PARTY ledger lands on.
// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// Date formatter — handles both YYYYMMDD (Tally) and YYYY-MM-DD (DB) formats
// ---------------------------------------------------------------------------
function formatVoucherDate(raw: string): string {
    if (!raw) return "—";
    try {
        const normalized = raw.length === 8
            ? `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`
            : raw.slice(0, 10);
        const d = new Date(normalized + "T00:00:00");
        if (isNaN(d.getTime())) return raw;
        return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch {
        return raw;
    }
}

const CREDIT_VOUCHER_TYPES = new Set([
    // Supplier is CREDITED — we owe them / goods/cash coming in
    'Purchase',          // Dr Purchase A/c  | Cr Supplier
    'Receipt',           // Dr Cash/Bank      | Cr Customer (settling receivable)
    'Credit Note',       // Dr Sales Returns  | Cr Customer (reducing receivable)
    'Contra',            // Dr Cash           | Cr Bank (internal transfer)
    'Receipt Note',      // Stock inward — like a purchase
    'Rejection Out',     // Goods returned to supplier — Dr Supplier, Cr Stock
    'Purchase Order',    // Future purchase obligation — credit intent
]);

const DEBIT_VOUCHER_TYPES = new Set([
    // Customer / party is DEBITED — they owe us / money/goods going out
    'Sales',             // Dr Customer       | Cr Sales A/c
    'Payment',           // Dr Supplier       | Cr Cash/Bank (paying off payable)
    'Debit Note',        // Dr Supplier       | Cr Purchase Returns
    'Delivery Note',     // Stock outward to customer
    'Sales Order',       // Future sale obligation — debit intent
    'Rejection In',      // Defective goods returned inward — Dr Stock, Cr Supplier
    // Ambiguous / no-party vouchers — shown on Debit side by convention
    'Journal',
    'Stock Journal',
    'Memorandum',
]);

/** Returns true if the voucher amount belongs in the Debit column */
function isDebitVoucher(type: string): boolean {
    if (DEBIT_VOUCHER_TYPES.has(type)) return true;
    // Any unknown type not in the credit set — default to debit so amount is always visible
    if (!CREDIT_VOUCHER_TYPES.has(type)) return true;
    return false;
}

/** Returns true if the voucher amount belongs in the Credit column */
function isCreditVoucher(type: string): boolean {
    return CREDIT_VOUCHER_TYPES.has(type);
}

// ---------------------------------------------------------------------------

interface Voucher {
    date: string;
    voucher_type: string;
    voucher_number: string;
    party_name: string;
    amount: number | string;
    narration: string;
    ledger_id?: number | string;
    id?: number;
}

interface DaybookTableProps {
    vouchers: Voucher[];
    loading: boolean;
    onViewDetails: (voucher: Voucher) => void;
    onDelete: (voucher: Voucher) => void;
    page: number;
    limit: number;
    totalCount: number;
    onPageChange: (page: number) => void;
    onLimitChange: (limit: number) => void;
}

export function DaybookTable({
    vouchers,
    loading,
    onViewDetails,
    onDelete,
    page,
    limit,
    totalCount,
    onPageChange,
    onLimitChange
}: DaybookTableProps) {
    if (loading) {
        return <div className="p-8 text-center text-muted-foreground animate-pulse">Loading daybook...</div>;
    }

    if (vouchers.length === 0) {
        return (
            <div className="p-12 text-center border-2 border-dashed rounded-lg bg-muted/10">
                <p className="text-muted-foreground font-medium">No transactions found for this period.</p>
                <Button variant="link" className="mt-2 text-primary">Clear all filters</Button>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="rounded-md border bg-white overflow-hidden shadow-sm">
                <Table>
                    <TableHeader className="bg-muted/40">
                        <TableRow>
                            <TableHead className="w-[120px]">Date</TableHead>
                            <TableHead className="w-[100px]">Vch No</TableHead>
                            <TableHead className="w-[100px]">Type</TableHead>
                            <TableHead>Particulars</TableHead>
                            <TableHead className="hidden md:table-cell text-right">Debit</TableHead>
                            <TableHead className="text-right">Credit</TableHead>
                            <TableHead className="w-[50px]"></TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {vouchers.map((voucher, idx) => (
                            <TableRow
                                key={idx}
                                className="cursor-pointer hover:bg-muted/30 group transition-colors"
                                onClick={() => onViewDetails(voucher)}
                            >
                                <TableCell className="font-medium text-muted-foreground whitespace-nowrap">
                                    {formatVoucherDate(voucher.date)}
                                </TableCell>
                                <TableCell className="text-xs font-mono text-muted-foreground">
                                    {voucher.voucher_number || "-"}
                                </TableCell>
                                <TableCell>
                                    <Badge
                                        variant="secondary"
                                        className={`font-normal text-xs px-2 ${
                                            // Credit-side vouchers → green
                                            ['Receipt', 'Purchase', 'Credit Note', 'Contra', 'Receipt Note', 'Rejection Out', 'Purchase Order'].includes(voucher.voucher_type)
                                                ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                                                // Debit-side vouchers → red/rose  
                                                : ['Payment', 'Sales', 'Debit Note', 'Delivery Note', 'Sales Order', 'Rejection In'].includes(voucher.voucher_type)
                                                    ? 'bg-rose-50 text-rose-700 hover:bg-rose-100'
                                                    // Journal / Stock Journal / Memo → amber
                                                    : ['Journal', 'Stock Journal', 'Memorandum'].includes(voucher.voucher_type)
                                                        ? 'bg-amber-50 text-amber-700 hover:bg-amber-100'
                                                        // Default fallback
                                                        : 'bg-blue-50 text-blue-700 hover:bg-blue-100'
                                            }`}
                                    >
                                        {voucher.voucher_type}
                                    </Badge>
                                </TableCell>
                                <TableCell>
                                    <div className="flex flex-col">
                                        {voucher.ledger_id ? (
                                            <Link
                                                href={`/parties?id=${voucher.ledger_id}`}
                                                className="font-medium text-foreground hover:underline hover:text-primary transition-colors"
                                                onClick={(e) => e.stopPropagation()}
                                            >
                                                {voucher.party_name}
                                            </Link>
                                        ) : (
                                            <span className="font-medium text-foreground">{voucher.party_name}</span>
                                        )}
                                        {voucher.narration && (
                                            <span className="text-[10px] text-muted-foreground truncate max-w-[200px] md:max-w-[300px] opacity-0 group-hover:opacity-100 transition-opacity">
                                                {voucher.narration}
                                            </span>
                                        )}
                                    </div>
                                </TableCell>
                                <TableCell className="hidden md:table-cell text-right font-mono text-sm text-rose-700">
                                    {/* DEBIT side — party is debited (customer owes us / supplier being reduced) */}
                                    {isDebitVoucher(voucher.voucher_type) &&
                                        <span>
                                            {Number(voucher.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                                        </span>
                                    }
                                </TableCell>
                                <TableCell className="text-right font-mono text-sm text-emerald-700">
                                    {/* CREDIT side — party is credited (supplier we owe / customer settled) */}
                                    {isCreditVoucher(voucher.voucher_type) &&
                                        <span>
                                            {Number(voucher.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                                        </span>
                                    }
                                </TableCell>
                                <TableCell>
                                    <div onClick={(e) => e.stopPropagation()}>
                                        <DropdownMenu>
                                            <DropdownMenuTrigger asChild>
                                                <Button variant="ghost" className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100">
                                                    <span className="sr-only">Open menu</span>
                                                    <MoreHorizontal className="h-4 w-4" />
                                                </Button>
                                            </DropdownMenuTrigger>
                                            <DropdownMenuContent align="end">
                                                <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                                <DropdownMenuItem onClick={() => onViewDetails(voucher)}>View Details</DropdownMenuItem>
                                                <DropdownMenuItem>Edit Voucher</DropdownMenuItem>
                                                <DropdownMenuSeparator />
                                                <DropdownMenuItem
                                                    className="text-destructive"
                                                    onClick={() => onDelete(voucher)}
                                                >
                                                    Delete
                                                </DropdownMenuItem>
                                            </DropdownMenuContent>
                                        </DropdownMenu>
                                    </div>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </div>

            {/* Pagination / Footer */}
            <div className="px-2">
                <PaginationControls
                    currentPage={page}
                    totalItems={totalCount}
                    itemsPerPage={limit}
                    onPageChange={onPageChange}
                    onLimitChange={onLimitChange}
                    isLoading={loading}
                />
            </div>
        </div>
    );
}
