"use client";

import { OperationsHeader } from "@/components/invoices/OperationsHeader";
import { QuickActions } from "@/components/invoices/QuickActions";
import { InvoiceStats } from "@/components/invoices/InvoiceStats";
import { InvoicesTable } from "@/components/invoices/InvoicesTable";

export default function InvoicesPageClient() {
    return (
        <div className="space-y-8 pb-12 max-w-[1600px] mx-auto">
            {/* Header Section */}
            <OperationsHeader />

            {/* Quick Actions & Summary Grid */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                <div className="xl:col-span-2">
                    <QuickActions />
                </div>
                <div className="xl:col-span-1 h-full">
                    <InvoiceStats />
                </div>
            </div>

            {/* Main Content Table */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <h2 className="text-lg font-semibold tracking-tight">Recent Transactions</h2>
                    {/* Optional: Add table-specific actions here like "Columns", "Export" */}
                </div>
                <InvoicesTable />
            </div>
        </div>
    );
}
