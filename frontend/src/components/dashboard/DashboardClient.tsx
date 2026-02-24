"use client";

import { useRouter } from "next/navigation";
import DashboardStats from "@/components/DashboardStats";
import { DashboardCharts } from "@/components/dashboard/DashboardCharts";
import { DashboardActions } from "@/components/dashboard/DashboardActions";
import { Button } from "@/components/ui/button";
import { Sparkles } from "lucide-react";

export default function DashboardClient() {
    const router = useRouter();

    return (
        <div className="space-y-8 pb-12 max-w-[1600px] mx-auto">

            {/* Page Header */}
            <div className="flex items-start justify-between">
                <div className="flex flex-col gap-1">
                    <h1 className="text-2xl font-bold tracking-tight text-slate-800">Dashboard</h1>
                    <p className="text-sm text-slate-500">
                        Your financial overview — synced from Tally.
                    </p>
                </div>

                {/* AI CTA — navigates to /chat instead of opening an inline input */}
                <Button
                    onClick={() => router.push("/chat")}
                    className="gap-2 bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-200 rounded-xl h-9 text-sm font-medium"
                >
                    <Sparkles className="h-3.5 w-3.5" />
                    Ask KITTU
                </Button>
            </div>

            {/* KPI Stats + Parties + Inventory */}
            <DashboardStats />

            {/* Cashflow & Receivable Charts */}
            <DashboardCharts />

            {/* Quick Actions */}
            <DashboardActions />

        </div>
    );
}
