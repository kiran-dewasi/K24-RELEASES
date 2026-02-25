"use client";

import { useState, useEffect, useMemo, useRef } from "react";
import { apiClient } from "@/lib/api-config";
import { DaybookFilterBar } from "@/components/daybook/DaybookFilterBar";
import { DaybookTable } from "@/components/daybook/DaybookTable";
import { VoucherDrawer } from "@/components/daybook/VoucherDrawer";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { DateFilterType, getDateRange, formatDateForDisplay, formatDateForApi } from "@/lib/date-utils";
import { DateRange } from "react-day-picker";

interface Voucher {
    date: string;
    voucher_type: string;
    voucher_number: string;
    party_name: string;
    amount: number | string;
    narration: string;
    ledger_id?: number | string;
}

export default function DayBookClient() {
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();

    // Derived Pagination State
    const page = Number(searchParams.get("page")) || 1;
    const limit = Number(searchParams.get("limit")) || 50;

    // Internal State
    const [vouchers, setVouchers] = useState<Voucher[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedVoucher, setSelectedVoucher] = useState<Voucher | null>(null);
    const [drawerOpen, setDrawerOpen] = useState(false);
    const [totalCount, setTotalCount] = useState(0);

    // Filter State
    const [filterType, setFilterType] = useState<DateFilterType>('today');
    const [customRange, setCustomRange] = useState<DateRange | undefined>();
    const [voucherType, setVoucherType] = useState<string>("all_types");
    const [searchQuery, setSearchQuery] = useState<string>("");

    // Ref for cancellation
    const abortControllerRef = useRef<AbortController | null>(null);

    // Helper to update URL
    const updatePagination = (newPage: number, newLimit: number) => {
        const params = new URLSearchParams(searchParams);
        params.set("page", newPage.toString());
        params.set("limit", newLimit.toString());
        router.push(`${pathname}?${params.toString()}`, { scroll: false });
    };

    // Load from LocalStorage on Mount
    useEffect(() => {
        const saved = localStorage.getItem('daybook_date_filter');
        const savedLimit = localStorage.getItem('daybook_limit');

        if (savedLimit) {
            const l = Number(savedLimit);
            if (l !== limit) updatePagination(1, l);
        }

        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                if (parsed.type) setFilterType(parsed.type as DateFilterType);
                if (parsed.startDate && parsed.endDate) {
                    setCustomRange({
                        from: new Date(parsed.startDate),
                        to: new Date(parsed.endDate)
                    });
                }
            } catch (e) {
                console.error("Failed to parse saved filter", e);
            }
        }
    }, []);

    // Save filters to LocalStorage on Change
    useEffect(() => {
        const data = {
            type: filterType,
            startDate: customRange?.from?.toISOString(),
            endDate: customRange?.to?.toISOString()
        };
        localStorage.setItem('daybook_date_filter', JSON.stringify(data));
    }, [filterType, customRange]);

    // Save limit to LocalStorage
    const handleLimitChange = (newLimit: number) => {
        localStorage.setItem('daybook_limit', newLimit.toString());
        updatePagination(1, newLimit);
    };

    // Calculate effective date range
    const activeRange = useMemo(() => {
        if (filterType === 'custom') {
            if (!customRange?.from) return null;
            return { from: customRange.from, to: customRange.to || customRange.from };
        }
        return getDateRange(filterType);
    }, [filterType, customRange]);

    // Reset Page on Filter Change
    useEffect(() => {
        // If we filter, we usually want to go back to page 1
        // But only if we aren't already there
        if (page !== 1) {
            updatePagination(1, limit);
        }
    }, [activeRange, voucherType, searchQuery]);

    // Fetch Data
    useEffect(() => {
        if (activeRange) {
            const timeoutId = setTimeout(() => {
                fetchVouchers();
            }, 300);
            return () => clearTimeout(timeoutId);
        }
    }, [activeRange, voucherType, searchQuery, page, limit]);

    const fetchVouchers = async () => {
        if (!activeRange) return;

        // Cancel previous request
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        const controller = new AbortController();
        abortControllerRef.current = controller;

        setLoading(true);
        try {
            const timeout = setTimeout(() => controller.abort(), 15000);

            const params = new URLSearchParams({
                start_date: formatDateForApi(activeRange.from),
                end_date: formatDateForApi(activeRange.to),
                page: page.toString(),
                limit: limit.toString()
            });

            if (voucherType !== "all_types") {
                params.append("voucher_type", voucherType);
            }

            if (searchQuery) {
                params.append("search_query", searchQuery);
            }

            const res = await apiClient(`/api/vouchers?${params.toString()}`, {
                signal: controller.signal
            });

            clearTimeout(timeout);

            if (!res.ok) throw new Error("Failed");

            const data = await res.json();

            // Normalize data
            let list = [];
            if (data.vouchers) {
                list = data.vouchers;
                setTotalCount(data.total_count || list.length);
            }
            else if (Array.isArray(data)) {
                list = data;
                setTotalCount(list.length);
            }
            else if (data.data) {
                list = data.data;
                setTotalCount(data.total || list.length);
            }

            setVouchers(list);
        } catch (err) {
            if ((err as Error).name === 'AbortError') {
                console.log("Request aborted");
                return;
            }
            console.error("Failed to fetch vouchers", err);
            setVouchers([]);
        } finally {
            if (abortControllerRef.current === controller) {
                setLoading(false);
            }
        }
    };

    // State for the detail fetch
    const [detailData, setDetailData] = useState<Record<string, unknown> | null>(null);
    const [detailLoading, setDetailLoading] = useState(false);

    const handleViewDetails = async (v: Voucher) => {
        setSelectedVoucher(v);
        setDetailData(null);
        setDrawerOpen(true);
        setDetailLoading(true);
        try {
            const params = new URLSearchParams({ voucher_number: v.voucher_number });
            if (v.voucher_type) params.append("voucher_type", v.voucher_type);
            const res = await apiClient(`/api/vouchers/detail?${params.toString()}`);
            if (res.ok) {
                const data = await res.json();
                setDetailData(data);
            }
        } catch (err) {
            console.error("Failed to fetch voucher detail", err);
        } finally {
            setDetailLoading(false);
        }
    };


    const getHeaderText = () => {
        if (!activeRange) return "";
        if (filterType === 'today') return `Daily Transactions for ${formatDateForDisplay(activeRange.from)}`;
        if (filterType === 'yesterday') return `Daily Transactions for ${formatDateForDisplay(activeRange.from)}`;
        return `Transactions from ${formatDateForDisplay(activeRange.from)} to ${formatDateForDisplay(activeRange.to)}`;
    };

    return (
        <div className="space-y-6 pb-24 max-w-[1600px] mx-auto">
            {/* Header Area */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Daybook - {getHeaderText()}</h1>
                    <p className="text-muted-foreground mt-1">
                        Review, audit and manage daily financial transactions.
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button className="bg-primary text-primary-foreground hover:bg-primary/90 gap-2" onClick={() => router.push('/vouchers/new/sales')}>
                        <Plus className="h-4 w-4" /> New Entry
                    </Button>
                </div>
            </div>

            {/* Filter Bar */}
            <DaybookFilterBar
                filterType={filterType}
                onFilterChange={setFilterType}
                customDateRange={customRange}
                onCustomRangeChange={setCustomRange}
                voucherType={voucherType}
                onVoucherTypeChange={setVoucherType}
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
            />

            {/* Main Table */}
            <DaybookTable
                vouchers={vouchers}
                loading={loading}
                onViewDetails={handleViewDetails}
                page={page}
                limit={limit}
                totalCount={totalCount}
                onPageChange={(p) => updatePagination(p, limit)}
                onLimitChange={handleLimitChange}
            />

            {/* Detail Drawer */}
            <VoucherDrawer
                open={drawerOpen}
                onClose={() => setDrawerOpen(false)}
                voucher={selectedVoucher}
                detailData={detailData}
                detailLoading={detailLoading}
            />
        </div>
    );
}
