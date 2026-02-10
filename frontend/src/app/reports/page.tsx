"use client";

import { ReportsGrid } from "@/components/reports/ReportsGrid";
import { Button } from "@/components/ui/button";
import { Calendar, Filter, Share2 } from "lucide-react";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";

export default function ReportsPage() {
    return (
        <div className="space-y-8 pb-12 max-w-[1600px] mx-auto">

            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Intelligence Reports</h1>
                    <p className="text-muted-foreground mt-1">Deep dive into your business performance with AI-enhanced analytics.</p>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline" className="gap-2">
                        <Share2 className="h-4 w-4" /> Export All
                    </Button>
                </div>
            </div>

            {/* Filter Bar */}
            <div className="flex flex-wrap items-center gap-3 p-1 rounded-lg">
                <Select defaultValue="tally_demo">
                    <SelectTrigger className="w-[180px] bg-white">
                        <SelectValue placeholder="Select Company" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="tally_demo">Tally Demo Co.</SelectItem>
                        <SelectItem value="k24_tech">K24 Technologies</SelectItem>
                    </SelectContent>
                </Select>

                <Button variant="outline" className="bg-white gap-2 text-muted-foreground font-normal">
                    <Calendar className="h-4 w-4" /> This Financial Year
                </Button>

                <Button variant="ghost" className="gap-2 text-primary">
                    <Filter className="h-4 w-4" /> More Filters
                </Button>

                <div className="ml-auto hidden md:flex gap-2">
                    <Badge variant="secondary">FY 2025-26</Badge>
                </div>
            </div>

            {/* Reports Grid */}
            <ReportsGrid />
        </div>
    );
}
