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

interface Voucher {
    date: string;
    voucher_type: string;
    voucher_number: string;
    party_name: string;
    amount: number;
    narration: string;
    ledger_id?: number | string;
}

interface DaybookTableProps {
    vouchers: Voucher[];
    loading: boolean;
    onViewDetails: (voucher: Voucher) => void;
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
                                    {voucher.date}
                                </TableCell>
                                <TableCell className="text-xs font-mono text-muted-foreground">
                                    {voucher.voucher_number || "-"}
                                </TableCell>
                                <TableCell>
                                    <Badge
                                        variant="secondary"
                                        className={`font-normal text-xs px-2 ${voucher.voucher_type === 'Receipt' ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100' :
                                            voucher.voucher_type === 'Payment' ? 'bg-rose-50 text-rose-700 hover:bg-rose-100' :
                                                'bg-blue-50 text-blue-700 hover:bg-blue-100'
                                            }`}
                                    >
                                        {voucher.voucher_type}
                                    </Badge>
                                </TableCell>
                                <TableCell>
                                    <div className="flex flex-col">
                                        {voucher.ledger_id ? (
                                            <Link
                                                href={`/parties/${voucher.ledger_id}`}
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
                                <TableCell className="hidden md:table-cell text-right font-mono text-sm">
                                    {/* Debit Side Types */}
                                    {['Payment', 'Purchase', 'Journal', 'Debit Note'].includes(voucher.voucher_type) &&
                                        <span className="text-foreground">
                                            {voucher.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                                        </span>
                                    }
                                </TableCell>
                                <TableCell className="text-right font-mono text-sm">
                                    {/* Credit Side Types */}
                                    {['Receipt', 'Sales', 'Contra', 'Credit Note'].includes(voucher.voucher_type) &&
                                        <span className="text-foreground">
                                            {voucher.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
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
                                                <DropdownMenuItem className="text-destructive">Delete</DropdownMenuItem>
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
