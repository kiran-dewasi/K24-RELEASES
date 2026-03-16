"use client";

import { useEffect, useState, useMemo } from "react";
import { api } from "@/lib/api";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
    TableFooter
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { Calendar as CalendarIcon, Search, Filter, Download } from "lucide-react";
import { DateRange } from "react-day-picker"; // Using date-fns or similar
import { formatDateForDisplay, formatDateForApi, getDateRange } from "@/lib/date-utils";
import { cn } from "@/lib/utils";

interface Transaction {
    id: number;
    date: string;
    voucher_number: string;
    voucher_type: string;
    amount: number;
    narration: string;
    // Computed on frontend
    running_balance?: number;
    debit?: number;
    credit?: number;
}

interface LedgerTransactionsTabProps {
    ledgerId: number;
}

export function LedgerTransactionsTab({ ledgerId }: LedgerTransactionsTabProps) {
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [loading, setLoading] = useState(true);
    const [counts, setCounts] = useState(0);
    const [openingBal, setOpeningBal] = useState(0);

    // Filters
    const [dateRange, setDateRange] = useState<DateRange | undefined>(getDateRange('this_fy'));
    const [voucherType, setVoucherType] = useState<string>("all");
    const [searchTerm, setSearchTerm] = useState("");
    const [debouncedSearch, setDebouncedSearch] = useState("");

    // Debounce search
    useEffect(() => {
        const timer = setTimeout(() => setDebouncedSearch(searchTerm), 500);
        return () => clearTimeout(timer);
    }, [searchTerm]);

    // Fetch Data
    useEffect(() => {
        fetchTransactions();
    }, [ledgerId, dateRange, voucherType, debouncedSearch]);

    const fetchTransactions = async () => {
        setLoading(true);
        try {
            const query = new URLSearchParams({
                limit: "1000", // High limit for running bal view
                offset: "0"
            });

            if (dateRange?.from) query.append("start_date", formatDateForApi(dateRange.from));
            if (dateRange?.to) query.append("end_date", formatDateForApi(dateRange.to));
            if (voucherType !== 'all') query.append("voucher_type", voucherType);
            if (debouncedSearch) query.append("search", debouncedSearch);

            const res = await api.get(`/api/ledgers/${ledgerId}/transactions?${query.toString()}`);
            if (res.ok) {
                const data = await res.json();
                processTransactions(data.transactions, data.opening_balance);
                setCounts(data.count);
                setOpeningBal(data.opening_balance);
            }
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    const processTransactions = (rawTxns: any[], opBal: number) => {
        let running = opBal;
        const processed = rawTxns.map((tx: any) => {
            const type = (tx.voucher_type || "").toLowerCase();
            const amt = tx.amount;

            // Determine Dr/Cr
            // Logic must match Backend logic for consistency!
            let dr = 0;
            let cr = 0;

            const isDebit = ['sales', 'payment', 'debit note', 'journal'].some(t => type.includes(t));

            // Standardizing assumption: Vouchers usually usually +ve in DB.
            // If backend logic was simply 'balance += amt' for Debit and '-= amt' for Credit.

            if (isDebit) {
                dr = amt;
                running += amt;
            } else {
                cr = amt;
                running -= amt;
            }

            return {
                ...tx,
                debit: dr,
                credit: cr,
                running_balance: running
            };
        });
        setTransactions(processed);
    };

    const formatCurrency = (val: number | undefined) => {
        if (val === undefined) return "-";
        return Math.abs(val).toLocaleString('en-IN', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    };

    // Calculate Footer Totals
    const totalDr = transactions.reduce((acc, curr) => acc + (curr.debit || 0), 0);
    const totalCr = transactions.reduce((acc, curr) => acc + (curr.credit || 0), 0);
    const closingBal = openingBal + totalDr - totalCr;

    return (
        <div className="space-y-4">

            {/* Filter Bar */}
            <div className="flex flex-col md:flex-row gap-4 p-4 bg-muted/20 rounded-lg border">

                {/* Date Picker */}
                <Popover>
                    <PopoverTrigger asChild>
                        <Button variant="outline" className={cn("w-[240px] justify-start text-left font-normal", !dateRange && "text-muted-foreground")}>
                            <CalendarIcon className="mr-2 h-4 w-4" />
                            {dateRange?.from ? (
                                dateRange.to ? (
                                    <>{formatDateForDisplay(dateRange.from)} - {formatDateForDisplay(dateRange.to)}</>
                                ) : (
                                    formatDateForDisplay(dateRange.from)
                                )
                            ) : (
                                <span>Pick a date range</span>
                            )}
                        </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0" align="start">
                        <Calendar
                            initialFocus
                            mode="range"
                            defaultMonth={dateRange?.from}
                            selected={dateRange}
                            onSelect={setDateRange}
                            numberOfMonths={2}
                        />
                    </PopoverContent>
                </Popover>

                {/* Voucher Type */}
                <Select value={voucherType} onValueChange={setVoucherType}>
                    <SelectTrigger className="w-[180px]">
                        <SelectValue placeholder="Voucher Type" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">All Vouchers</SelectItem>
                        <SelectItem value="sales">Sales</SelectItem>
                        <SelectItem value="purchase">Purchase</SelectItem>
                        <SelectItem value="receipt">Receipt</SelectItem>
                        <SelectItem value="payment">Payment</SelectItem>
                    </SelectContent>
                </Select>

                {/* Search */}
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Search Voucher No, Narration..."
                        className="pl-9"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>

                <Button variant="outline" size="icon">
                    <Download className="h-4 w-4" />
                </Button>
            </div>

            {/* Transactions Table */}
            <div className="rounded-md border bg-white overflow-hidden">
                <Table>
                    <TableHeader className="bg-muted/50">
                        <TableRow>
                            <TableHead className="w-[100px]">Date</TableHead>
                            <TableHead>Particulars</TableHead> {/* Type + No + Narration */}
                            <TableHead className="text-right w-[120px]">Debit (₹)</TableHead>
                            <TableHead className="text-right w-[120px]">Credit (₹)</TableHead>
                            <TableHead className="text-right w-[140px] bg-muted/20">Balance (₹)</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {/* Opening Balance Row */}
                        <TableRow className="bg-yellow-50/50 hover:bg-yellow-50">
                            <TableCell className="font-medium italic text-muted-foreground">Opening</TableCell>
                            <TableCell className="italic text-muted-foreground">Opening Balance Brought Forward</TableCell>
                            <TableCell className="text-right text-muted-foreground">-</TableCell>
                            <TableCell className="text-right text-muted-foreground">-</TableCell>
                            <TableCell className="text-right font-medium bg-yellow-50/50">
                                {formatCurrency(openingBal)} {openingBal >= 0 ? "Dr" : "Cr"}
                            </TableCell>
                        </TableRow>

                        {loading ? (
                            <TableRow>
                                <TableCell colSpan={5} className="h-24 text-center">Loading transactions...</TableCell>
                            </TableRow>
                        ) : transactions.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={5} className="h-24 text-center">No transactions found for this period.</TableCell>
                            </TableRow>
                        ) : (
                            transactions.map((tx) => (
                                <TableRow key={tx.id} className="cursor-pointer hover:bg-muted/10">
                                    <TableCell className="align-top whitespace-nowrap">
                                        {formatDateForDisplay(new Date(tx.date))}
                                    </TableCell>
                                    <TableCell className="align-top">
                                        <div className="flex flex-col gap-1">
                                            <div className="flex items-center gap-2">
                                                <span className="font-semibold text-primary/80 hover:underline">{tx.voucher_type}</span>
                                                <Badge variant="outline" className="text-[10px] font-mono">{tx.voucher_number}</Badge>
                                            </div>
                                            <span className="text-xs text-muted-foreground line-clamp-2">{tx.narration}</span>
                                        </div>
                                    </TableCell>
                                    <TableCell className="text-right align-top font-mono text-emerald-700">
                                        {tx.debit ? formatCurrency(tx.debit) : ""}
                                    </TableCell>
                                    <TableCell className="text-right align-top font-mono text-rose-700">
                                        {tx.credit ? formatCurrency(tx.credit) : ""}
                                    </TableCell>
                                    <TableCell className="text-right align-top font-mono font-medium bg-muted/5">
                                        {formatCurrency(tx.running_balance)} {(tx.running_balance || 0) >= 0 ? "Dr" : "Cr"}
                                    </TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                    <TableFooter className="bg-muted/50 font-medium">
                        <TableRow>
                            <TableCell colSpan={2}>Totals</TableCell>
                            <TableCell className="text-right text-emerald-700">{formatCurrency(totalDr)}</TableCell>
                            <TableCell className="text-right text-rose-700">{formatCurrency(totalCr)}</TableCell>
                            <TableCell className="text-right bg-muted/20">
                                {formatCurrency(closingBal)} {closingBal >= 0 ? "Dr" : "Cr"}
                            </TableCell>
                        </TableRow>
                    </TableFooter>
                </Table>
            </div>

            <p className="text-xs text-muted-foreground text-center">
                Showing {transactions.length} transactions.
            </p>
        </div>
    );
}
