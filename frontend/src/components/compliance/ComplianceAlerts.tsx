"use client";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle, TrendingUp } from "lucide-react";

export function ComplianceAlerts() {
    return (
        <div className="space-y-4">
            <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wider">Risk Radar</h3>
            <Alert variant="destructive" className="bg-red-50 text-red-900 border-red-200">
                <AlertCircle className="h-4 w-4 text-red-900" />
                <AlertTitle className="ml-2 font-semibold">TDS Payment Overdue</AlertTitle>
                <AlertDescription className="ml-2 mt-1 text-xs">
                    Contractor payments for Sep 2024 are overdue by 2 days. Penalty accumulating.
                </AlertDescription>
            </Alert>

            <Alert className="bg-amber-50 text-amber-900 border-amber-200">
                <TrendingUp className="h-4 w-4 text-amber-900" />
                <AlertTitle className="ml-2 font-semibold">High Input Credit</AlertTitle>
                <AlertDescription className="ml-2 mt-1 text-xs">
                    Input Tax Credit is 40% higher than last month average. Verify purchase invoices.
                </AlertDescription>
            </Alert>
        </div>
    );
}
