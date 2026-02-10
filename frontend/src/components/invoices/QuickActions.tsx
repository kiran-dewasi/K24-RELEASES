"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { FileText, TrendingUp, TrendingDown, ArrowDownToLine } from "lucide-react";

export function QuickActions() {
    const actions = [
        {
            title: "Sales Invoice",
            desc: "Create new GST invoice",
            icon: FileText,
            color: "text-blue-600",
            bg: "bg-blue-50",
            badge: "GST Compliant",
            href: "/vouchers/new/sales"
        },
        {
            title: "Record Receipt",
            desc: "Money in from customers",
            icon: TrendingUp,
            color: "text-emerald-600",
            bg: "bg-emerald-50",
            badge: "Updates Tally",
            href: "/vouchers/new/receipt"
        },
        {
            title: "Record Payment",
            desc: "Money out to vendors",
            icon: TrendingDown,
            color: "text-orange-600",
            bg: "bg-orange-50",
            badge: "Auto-Ledger",
            href: "/vouchers/new/payment"
        },
        {
            title: "Import / Sync",
            desc: "Pull recent Tally data",
            icon: ArrowDownToLine,
            color: "text-purple-600",
            bg: "bg-purple-50",
            badge: "One-Click",
            href: "/settings"
        }
    ];

    return (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {actions.map((action, i) => (
                <Link key={i} href={action.href}>
                    <Card className="hover:bg-muted/50 cursor-pointer transition-colors border shadow-sm h-full">
                        <CardContent className="p-4 flex flex-col gap-3">
                            <div className="flex justify-between items-start">
                                <div className={`p-2 rounded-lg ${action.bg} ${action.color}`}>
                                    <action.icon className="h-5 w-5" />
                                </div>
                                <Badge variant="secondary" className="text-[10px] h-5">
                                    {action.badge}
                                </Badge>
                            </div>
                            <div>
                                <h3 className="font-semibold text-sm">{action.title}</h3>
                                <p className="text-xs text-muted-foreground">{action.desc}</p>
                            </div>
                        </CardContent>
                    </Card>
                </Link>
            ))}
        </div>
    );
}
