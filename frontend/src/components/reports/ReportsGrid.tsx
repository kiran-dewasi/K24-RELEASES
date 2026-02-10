"use client";

import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, ShoppingCart, Wallet, Scale, TrendingDown, FileText, ArrowRight, Sparkles } from "lucide-react";
import Link from "next/link";

const reports = [
    {
        title: "Sales Register",
        icon: TrendingUp,
        color: "text-blue-600",
        bg: "bg-blue-50",
        href: "/reports/sales-register",
        desc: "Detailed breakdown of all sales invoices, credit notes, and customer trends.",
        ai_enhanced: true
    },
    {
        title: "Purchase Register",
        icon: ShoppingCart,
        color: "text-orange-600",
        bg: "bg-orange-50",
        href: "/reports/purchase-register",
        desc: "Track vendor expenses, purchase orders, and input tax credits.",
        ai_enhanced: false
    },
    {
        title: "Cash Flow",
        icon: Wallet,
        color: "text-emerald-600",
        bg: "bg-emerald-50",
        href: "/reports/cash-flow",
        desc: "Real-time visibility into cash inflows and outflows.",
        ai_enhanced: true
    },
    {
        title: "Balance Sheet",
        icon: Scale,
        color: "text-purple-600",
        bg: "bg-purple-50",
        href: "/reports/balance-sheet",
        desc: "A snapshot of your company's financial standing.",
        ai_enhanced: false
    },
    {
        title: "Profit & Loss",
        icon: TrendingDown,
        color: "text-red-600",
        bg: "bg-red-50",
        href: "/reports/profit-loss",
        desc: "Net profit analysis with month-on-month growth metrics.",
        ai_enhanced: true
    },
    {
        title: "GST Summary",
        icon: FileText,
        color: "text-indigo-600",
        bg: "bg-indigo-50",
        href: "/reports/gst-summary",
        desc: "Reconciliation of GSTR-1, 2A/2B and 3B.",
        ai_enhanced: true
    },
];

export function ReportsGrid() {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {reports.map((report, idx) => (
                <Link href={report.href} key={idx} className="block group h-full">
                    <Card className="h-full border hover:border-primary/50 hover:shadow-md transition-all cursor-pointer flex flex-col">
                        <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
                            <div className={`p-2.5 rounded-lg ${report.bg}`}>
                                <report.icon className={`h-6 w-6 ${report.color}`} />
                            </div>
                            {report.ai_enhanced && (
                                <Badge variant="secondary" className="bg-primary/5 text-primary border-primary/20 text-xs gap-1">
                                    <Sparkles className="h-3 w-3" /> AI Enhanced
                                </Badge>
                            )}
                        </CardHeader>
                        <CardContent className="pt-4 flex-1">
                            <CardTitle className="text-lg font-semibold mb-2 group-hover:text-primary transition-colors">
                                {report.title}
                            </CardTitle>
                            <p className="text-sm text-muted-foreground leading-relaxed">
                                {report.desc}
                            </p>
                        </CardContent>
                        <CardFooter className="pt-0 text-xs font-medium text-primary opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
                            Key metrics & trends <ArrowRight className="h-3 w-3" />
                        </CardFooter>
                    </Card>
                </Link>
            ))}
        </div>
    );
}
