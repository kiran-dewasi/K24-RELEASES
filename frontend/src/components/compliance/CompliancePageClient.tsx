"use client";

import { ComplianceStats } from "@/components/compliance/ComplianceStats";
import { ComplianceTimeline } from "@/components/compliance/ComplianceTimeline";
import { ComplianceChecklist } from "@/components/compliance/ComplianceChecklist";
import { ComplianceAlerts } from "@/components/compliance/ComplianceAlerts";
import { ShieldCheck } from "lucide-react";

export default function CompliancePageClient() {
    return (
        <div className="space-y-8 pb-12 max-w-[1600px] mx-auto">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                    <div className="bg-primary/10 p-2 rounded-lg">
                        <ShieldCheck className="h-8 w-8 text-primary" />
                    </div>
                    Compliance & Filings
                </h1>
                <p className="text-muted-foreground mt-2 text-lg">Stay ahead of GST, TDS, and statutory deadlines.</p>
            </div>

            {/* Summary Ribbon */}
            <ComplianceStats />

            {/* Main Split Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

                {/* Left Column: Timeline & Alerts (4 Cols) */}
                <div className="lg:col-span-4 space-y-8">
                    <div className="bg-white p-6 rounded-xl border shadow-sm">
                        <ComplianceTimeline />
                    </div>
                    <ComplianceAlerts />
                </div>

                {/* Right Column: Checklists (8 Cols) */}
                <div className="lg:col-span-8 space-y-6">
                    <h2 className="text-xl font-semibold tracking-tight">Active Obligations</h2>
                    <ComplianceChecklist />
                </div>
            </div>
        </div>
    );
}
