"use client";

import { useState } from "react";
import MagicInput from "@/components/MagicInput";
import DashboardStats from "@/components/DashboardStats";
import { DashboardCharts } from "@/components/dashboard/DashboardCharts";
import { DashboardActions } from "@/components/dashboard/DashboardActions";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Sparkles } from "lucide-react";

export default function DashboardClient() {
    return (
        <div className="space-y-8 pb-12 max-w-[1600px] mx-auto">

            {/* Header Section */}
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight">Overview</h1>
                <p className="text-muted-foreground text-lg">
                    Welcome back, here's what's happening today.
                </p>
            </div>

            {/* AI Command Center */}
            <section className="relative">
                <div className="bg-gradient-to-r from-indigo-50/50 to-purple-50/50 border rounded-xl p-1 shadow-sm transition-all hover:shadow-md hover:border-indigo-100">
                    <div className="flex items-center gap-3 bg-white rounded-lg px-4 py-2">
                        <Sparkles className="h-5 w-5 text-indigo-500 animate-pulse" />
                        <div className="flex-1">
                            <MagicInput isFullPage={false} placeholder="Ask KITTU: 'Show top customers' or 'Create invoice for Acme'" />
                        </div>
                    </div>
                </div>
                <p className="text-xs text-muted-foreground mt-2 px-1">
                    Try asking: <span className="font-medium text-foreground">"Who owes me money?"</span> or <span className="font-medium text-foreground">"Draft an invoice for Tally Solutions"</span>
                </p>
            </section>

            {/* Main Content Tabs */}
            <Tabs defaultValue="overview" className="w-full space-y-6" suppressHydrationWarning>
                <TabsList className="bg-transparent p-0 h-auto space-x-6 border-b w-full justify-start rounded-none">
                    <TabsTrigger
                        value="overview"
                        className="rounded-none border-b-2 border-transparent px-2 py-3 font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:text-primary data-[state=active]:shadow-none data-[state=active]:bg-transparent transition-none"
                    >
                        Overview
                    </TabsTrigger>
                    <TabsTrigger
                        value="reports"
                        className="rounded-none border-b-2 border-transparent px-2 py-3 font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:text-primary data-[state=active]:shadow-none data-[state=active]:bg-transparent transition-none"
                    >
                        Reports
                    </TabsTrigger>
                    <TabsTrigger
                        value="operations"
                        className="rounded-none border-b-2 border-transparent px-2 py-3 font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:text-primary data-[state=active]:shadow-none data-[state=active]:bg-transparent transition-none"
                    >
                        Operations
                    </TabsTrigger>
                    <TabsTrigger
                        value="compliance"
                        className="rounded-none border-b-2 border-transparent px-2 py-3 font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:text-primary data-[state=active]:shadow-none data-[state=active]:bg-transparent transition-none"
                    >
                        Compliance
                    </TabsTrigger>
                </TabsList>

                {/* OVERVIEW TAB */}
                <TabsContent value="overview" className="space-y-8 animate-in fade-in-50 duration-300">
                    <DashboardStats />
                    <DashboardCharts />
                    <DashboardActions />
                </TabsContent>

                {/* Other Tabs (Placeholders) */}
                <TabsContent value="reports" className="space-y-4">
                    <div className="p-12 text-center border-2 border-dashed rounded-lg bg-slate-50/50">
                        <p className="text-muted-foreground">Jump to the <span className="font-medium text-primary cursor-pointer hover:underline">Reports Module</span> for deep dives.</p>
                    </div>
                </TabsContent>

                <TabsContent value="operations" className="space-y-4">
                    <div className="p-12 text-center border-2 border-dashed rounded-lg bg-slate-50/50">
                        <p className="text-muted-foreground">Manage ongoing transactions in <span className="font-medium text-primary cursor-pointer hover:underline">Daybook</span>.</p>
                    </div>
                </TabsContent>

                <TabsContent value="compliance" className="space-y-4">
                    <div className="p-12 text-center border-2 border-dashed rounded-lg bg-slate-50/50">
                        <p className="text-muted-foreground">Audit logs and tax items are in <span className="font-medium text-primary cursor-pointer hover:underline">Compliance</span>.</p>
                    </div>
                </TabsContent>

            </Tabs>

        </div>
    );
}
