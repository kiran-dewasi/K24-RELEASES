"use client";

import { Button } from "@/components/ui/button";
import { Calendar } from "lucide-react";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Filter } from "lucide-react";

export function OperationsHeader() {
    return (
        <div className="space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Invoices & Operations</h1>
                    <p className="text-muted-foreground">Manage your vouchers, receipts, and payments.</p>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline" className="gap-2">
                        <Calendar className="h-4 w-4" />
                        Last 30 Days
                    </Button>
                    <Button variant="default">
                        + New Invoice
                    </Button>
                    {/* Secondary Buttons could be in a dropdown or just distinct buttons depending on space. 
                         User asked for secondary "+ Receipt", "+ Payment".
                      */}
                    <Button variant="outline" className="text-emerald-600 border-emerald-200 hover:bg-emerald-50">
                        + Receipt
                    </Button>
                    <Button variant="outline" className="text-orange-600 border-orange-200 hover:bg-orange-50">
                        + Payment
                    </Button>
                </div>
            </div>

            {/* Filters Row */}
            <div className="flex flex-wrap items-center gap-2">
                <Button variant="secondary" size="sm" className="bg-primary/10 text-primary hover:bg-primary/20">
                    All Transactions
                </Button>
                <Button variant="ghost" size="sm" className="text-muted-foreground border border-dashed">
                    Unpaid
                </Button>
                <Button variant="ghost" size="sm" className="text-muted-foreground border border-dashed">
                    Overdue
                </Button>
                <Button variant="ghost" size="sm" className="text-muted-foreground border border-dashed">
                    Paid
                </Button>
                <Button variant="ghost" size="sm" className="text-muted-foreground border border-dashed">
                    Draft
                </Button>

                <div className="ml-auto">
                    <Button variant="ghost" size="sm" className="gap-2">
                        <Filter className="h-4 w-4" /> Filter
                    </Button>
                </div>
            </div>
        </div>
    );
}
