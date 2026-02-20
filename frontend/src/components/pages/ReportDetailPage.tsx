"use client";

import { Suspense } from "react";
import { KittuInsightBar } from "@/components/reports/KittuInsightBar";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ArrowLeft, Calendar, Download, Filter, SlidersHorizontal, Loader2 } from "lucide-react";
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Badge } from "@/components/ui/badge";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";



function ReportDetailContent() {
    const searchParams = useSearchParams();
    const slug = searchParams.get('slug') || '';

    if (slug === 'default') {
        return <div className="p-8 text-center text-muted-foreground">Select a report to view details.</div>;
    }

    // Format title from slug
    const title = slug.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');

    return (
        <div className="flex flex-col h-[calc(100vh-8rem)]">

            {/* Header Area */}
            <div className="flex flex-col gap-4 mb-6">
                <div className="flex items-center gap-2 text-muted-foreground text-sm">
                    <Link href="/reports" className="hover:text-foreground transition-colors">Reports</Link>
                    <span>/</span>
                    <span className="text-foreground font-medium">{title}</span>
                </div>

                <div className="flex items-center justify-between">
                    <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
                    <div className="flex items-center gap-2">
                        <KittuInsightBar context={title} />
                        <div className="h-6 w-px bg-border mx-2"></div>
                        <Button variant="outline" size="sm" className="gap-2">
                            <Download className="h-4 w-4" /> Export
                        </Button>
                    </div>
                </div>
            </div>

            {/* Main Content: Two Pane Layout */}
            <div className="flex-1 flex gap-6 overflow-hidden">

                {/* Left Pane: Filters (Sticky/Scrollable) */}
                <Card className="w-64 flex-shrink-0 flex flex-col h-full bg-muted/10 border-r-0 shadow-sm">
                    <div className="p-4 border-b flex items-center justify-between">
                        <span className="font-semibold text-sm flex items-center gap-2">
                            <SlidersHorizontal className="h-4 w-4" /> Filters
                        </span>
                        <Button variant="ghost" size="sm" className="h-6 text-xs text-muted-foreground">Reset</Button>
                    </div>
                    <div className="flex-1 overflow-y-auto p-4 space-y-6">
                        {/* Mock Filters */}
                        <div className="space-y-2">
                            <label className="text-xs font-semibold text-muted-foreground uppercase">Date Range</label>
                            <Select defaultValue="this_month">
                                <SelectTrigger className="w-full bg-white">
                                    <SelectValue placeholder="Select range" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="this_month">This Month</SelectItem>
                                    <SelectItem value="last_month">Last Month</SelectItem>
                                    <SelectItem value="this_quarter">This Quarter</SelectItem>
                                    <SelectItem value="custom">Custom Range</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-3">
                            <label className="text-xs font-semibold text-muted-foreground uppercase">Voucher Type</label>
                            <div className="space-y-2">
                                <div className="flex items-center gap-2">
                                    <Checkbox id="sales" checked />
                                    <label htmlFor="sales" className="text-sm font-medium">Sales</label>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Checkbox id="cn" />
                                    <label htmlFor="cn" className="text-sm font-medium">Credit Note</label>
                                </div>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-xs font-semibold text-muted-foreground uppercase">Party Group</label>
                            <Select defaultValue="all">
                                <SelectTrigger className="w-full bg-white">
                                    <SelectValue placeholder="Select Group" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All Groups</SelectItem>
                                    <SelectItem value="sundry_debtors">Sundry Debtors</SelectItem>
                                    <SelectItem value="north_zone">North Zone</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <div className="p-4 border-t bg-white">
                        <Button className="w-full">Apply Filters</Button>
                    </div>
                </Card>

                {/* Right Pane: Data & Charts (Scrollable) */}
                <div className="flex-1 flex flex-col overflow-hidden bg-white rounded-lg border shadow-sm">
                    {/* Toolbar */}
                    <div className="h-12 border-b flex items-center px-4 justify-between bg-muted/5">
                        <div className="flex items-center gap-2">
                            <Badge variant="secondary" className="font-normal text-muted-foreground">32 Records Found</Badge>
                        </div>
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                            <span>Total Sales: <span className="text-foreground font-semibold">₹24,50,000</span></span>
                            <span>Tax: <span className="text-foreground font-semibold">₹4,41,000</span></span>
                        </div>
                    </div>

                    {/* Chart Section (Collapsible placeholder) */}
                    <div className="h-48 border-b bg-gray-50 flex items-center justify-center relative group">
                        <div className="text-center">
                            <p className="text-sm text-muted-foreground font-medium">Interactive Chart</p>
                            <p className="text-xs text-muted-foreground mt-1">Sales Trend by Week</p>
                        </div>
                        {/* Placeholder bars */}
                        <div className="absolute inset-x-20 bottom-0 top-12 flex items-end justify-between px-12 gap-2 opacity-50">
                            {[40, 60, 45, 70, 80, 50, 60, 90, 75, 60, 80, 100].map((h, i) => (
                                <div key={i} className="flex-1 bg-blue-500/20 hover:bg-blue-500/40 transition-colors rounded-t-sm" style={{ height: `${h}%` }}></div>
                            ))}
                        </div>
                    </div>

                    {/* Data Table */}
                    <div className="flex-1 overflow-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="bg-muted/30 sticky top-0 z-10 text-xs uppercase text-muted-foreground font-semibold">
                                <tr>
                                    <th className="px-4 py-3">Date</th>
                                    <th className="px-4 py-3">Particulars</th>
                                    <th className="px-4 py-3">Voucher Type</th>
                                    <th className="px-4 py-3">Voucher No.</th>
                                    <th className="px-4 py-3 text-right">Debit</th>
                                    <th className="px-4 py-3 text-right">Credit</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y">
                                {[...Array(10)].map((_, i) => (
                                    <tr key={i} className="hover:bg-muted/20">
                                        <td className="px-4 py-2.5 whitespace-nowrap text-muted-foreground">01-Oct-2025</td>
                                        <td className="px-4 py-2.5 font-medium">ABC Technologies Pvt Ltd</td>
                                        <td className="px-4 py-2.5">Sales</td>
                                        <td className="px-4 py-2.5 text-xs font-mono text-muted-foreground">INV-2425-{100 + i}</td>
                                        <td className="px-4 py-2.5 text-right font-medium">₹{(24000 + i * 1000).toLocaleString('en-IN')}</td>
                                        <td className="px-4 py-2.5 text-right text-muted-foreground">-</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function ReportDetailPage() {
    return (
        <Suspense fallback={
            <div className="flex h-[calc(100vh-8rem)] items-center justify-center">
                <Loader2 className="animate-spin h-8 w-8 text-muted-foreground" />
            </div>
        }>
            <ReportDetailContent />
        </Suspense>
    );
}
