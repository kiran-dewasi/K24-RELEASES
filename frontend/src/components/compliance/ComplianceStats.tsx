"use client";

import { useState, useEffect } from "react";
import { API_CONFIG } from "@/lib/api-config";

import { Card } from "@/components/ui/card";
import { CheckCircle2, AlertCircle, Clock } from "lucide-react";

interface ComplianceStat {
    label: string;
    status: "Good" | "Attention" | "Pending";
    value: string;
    subtext: string;
}

interface DashboardStats {
    high_value_count: number;
    backdated_count: number;
    weekend_count: number;
    pending_tds: number;
}

export function ComplianceStats() {
    const [stats, setStats] = useState<ComplianceStat[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const res = await fetch(`${API_CONFIG.BASE_URL}/compliance/dashboard-stats`, {
                    headers: { "x-api-key": "k24-secret-key-123" }
                });
                const data: DashboardStats = await res.json();

                setStats([
                    {
                        label: "GST Liability",
                        status: "Good",
                        value: "₹0", // TODO: Wire up real GST calc endpoint 
                        subtext: "System check passed"
                    },
                    {
                        label: "TDS Liability",
                        status: (data?.pending_tds ?? 0) > 1000 ? "Attention" : "Good",
                        value: `₹${(data?.pending_tds ?? 0).toLocaleString('en-IN')}`,
                        subtext: (data?.pending_tds ?? 0) > 0 ? "Payment pending" : "No pending dues"
                    },
                    {
                        label: "High Value Txns",
                        status: (data?.high_value_count ?? 0) > 0 ? "Attention" : "Good",
                        value: (data?.high_value_count ?? 0).toString(),
                        subtext: "> ₹2 Lakhs"
                    },
                    {
                        label: "Backdated Entries",
                        status: (data?.backdated_count ?? 0) > 0 ? "Pending" : "Good",
                        value: (data?.backdated_count ?? 0).toString(),
                        subtext: "Requires Audit"
                    },
                ]);
            } catch (err) {
                console.error("Failed to fetch compliance stats", err);
            } finally {
                setLoading(false);
            }
        };

        fetchStats();
    }, []);

    if (loading) {
        return <div className="text-muted-foreground p-4">Loading compliance data...</div>;
    }

    return (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {stats.map((stat, i) => (
                <Card key={i} className="p-4 flex flex-col justify-between border-l-4 border-l-transparent data-[status=Good]:border-l-emerald-500 data-[status=Attention]:border-l-amber-500 data-[status=Pending]:border-l-blue-500" data-status={stat.status}>
                    <div className="flex justify-between items-start mb-2">
                        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{stat.label}</span>
                        {stat.status === "Good" && <CheckCircle2 className="h-4 w-4 text-emerald-500" />}
                        {stat.status === "Attention" && <AlertCircle className="h-4 w-4 text-amber-500" />}
                        {stat.status === "Pending" && <Clock className="h-4 w-4 text-blue-500" />}
                    </div>
                    <div>
                        <div className="text-2xl font-bold">{stat.value}</div>
                        <div className="text-xs text-muted-foreground mt-1">{stat.subtext}</div>
                    </div>
                </Card>
            ))}
        </div>
    );
}
