"use client";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search, Calendar as CalendarIcon, Filter, SlidersHorizontal, Download } from "lucide-react";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { Badge } from "@/components/ui/badge";

import { DateFilterType, formatDateForDisplay } from "@/lib/date-utils";
import { DateRange } from "react-day-picker";
import { cn } from "@/lib/utils";

interface DaybookFilterBarProps {
    filterType: DateFilterType;
    onFilterChange: (type: DateFilterType) => void;
    customDateRange: DateRange | undefined;
    onCustomRangeChange: (range: DateRange | undefined) => void;
    voucherType: string;
    onVoucherTypeChange: (type: string) => void;
    searchQuery: string;
    onSearchChange: (query: string) => void;
}

export function DaybookFilterBar({
    filterType,
    onFilterChange,
    customDateRange,
    onCustomRangeChange,
    voucherType,
    onVoucherTypeChange,
    searchQuery,
    onSearchChange
}: DaybookFilterBarProps) {


    return (
        <div className="flex flex-col md:flex-row gap-4 items-center bg-white p-2 rounded-lg border shadow-sm">

            {/* Search */}
            <div className="relative flex-1 w-full">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                    placeholder="Search by Voucher No, Party, or Amount..."
                    className="pl-9 border-none bg-muted/20 focus-visible:ring-1 focus-visible:bg-white transition-all"
                    value={searchQuery}
                    onChange={(e) => onSearchChange(e.target.value)}
                />
            </div>

            <div className="h-6 w-px bg-border hidden md:block" />

            {/* Filters Group */}
            <div className="flex items-center gap-2 w-full md:w-auto overflow-x-auto pb-2 md:pb-0">

                {/* Date Dropdown */}
                <div className="flex items-center gap-2">
                    <Select
                        value={filterType}
                        onValueChange={(val) => onFilterChange(val as DateFilterType)}
                    >
                        <SelectTrigger className="w-[180px] h-9 border-dashed">
                            <div className="flex items-center gap-2 text-muted-foreground">
                                <CalendarIcon className="h-4 w-4" />
                                <SelectValue placeholder="Date Range" />
                            </div>
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="today">Today</SelectItem>
                            <SelectItem value="yesterday">Yesterday</SelectItem>
                            <SelectItem value="this_week">This Week</SelectItem>
                            <SelectItem value="last_week">Last Week</SelectItem>
                            <SelectItem value="this_month">This Month</SelectItem>
                            <SelectItem value="last_month">Last Month</SelectItem>
                            <SelectItem value="this_quarter">This Quarter</SelectItem>
                            <SelectItem value="this_fy">This Financial Year</SelectItem>
                            <SelectItem value="custom">Custom Range...</SelectItem>
                        </SelectContent>
                    </Select>

                    {/* Custom Range Popover - Only show if 'custom' is selected */}
                    {filterType === 'custom' && (
                        <Popover>
                            <PopoverTrigger asChild>
                                <Button
                                    variant={"outline"}
                                    className={cn(
                                        "h-9 justify-start text-left font-normal border-dashed",
                                        !customDateRange && "text-muted-foreground"
                                    )}
                                >
                                    <CalendarIcon className="mr-2 h-4 w-4" />
                                    {customDateRange?.from ? (
                                        customDateRange.to ? (
                                            <>
                                                {formatDateForDisplay(customDateRange.from)} -{" "}
                                                {formatDateForDisplay(customDateRange.to)}
                                            </>
                                        ) : (
                                            formatDateForDisplay(customDateRange.from)
                                        )
                                    ) : (
                                        <span>Pick a date</span>
                                    )}
                                </Button>
                            </PopoverTrigger>
                            <PopoverContent className="w-auto p-0" align="start">
                                <Calendar
                                    initialFocus
                                    mode="range"
                                    defaultMonth={customDateRange?.from}
                                    selected={customDateRange}
                                    onSelect={onCustomRangeChange}
                                    numberOfMonths={2}
                                />
                            </PopoverContent>
                        </Popover>
                    )}
                </div>

                {/* Voucher Type */}
                <Select value={voucherType} onValueChange={onVoucherTypeChange}>
                    <SelectTrigger className="w-[140px] h-9 border-dashed text-muted-foreground">
                        <SelectValue placeholder="Type" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all_types">All Types</SelectItem>
                        <SelectItem value="sales">Sales</SelectItem>
                        <SelectItem value="purchase">Purchase</SelectItem>
                        <SelectItem value="receipt">Receipt</SelectItem>
                        <SelectItem value="payment">Payment</SelectItem>
                    </SelectContent>
                </Select>

                {/* Company Selector - Moved after date/type to de-emphasize */}
                <Select defaultValue="all">
                    <SelectTrigger className="w-[40px] md:w-[160px] h-9 border-dashed px-2 md:px-3 text-muted-foreground">
                        <span className="md:hidden">Co.</span>
                        <SelectValue placeholder="Company" className="hidden md:block" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">All Companies</SelectItem>
                        <SelectItem value="tally_demo">Tally Demo Co.</SelectItem>
                    </SelectContent>
                </Select>

            </div>

            <div className="h-6 w-px bg-border hidden md:block" />

            {/* Actions */}
            <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" className="h-9 gap-2 text-primary">
                    <Download className="h-4 w-4" />
                    <span className="hidden sm:inline">Export</span>
                </Button>
            </div>
        </div>
    );
}
