"use client";

import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Download, UploadCloud, RefreshCw } from "lucide-react";

interface Obligation {
    title: string;
    period: string;
    dueDate: string;
    status: "To File" | "Filed" | "Overdue";
    amount?: string;
}

const obligations: Obligation[] = [
    { title: "GSTR-1 (Sales)", period: "Oct 2024", dueDate: "Nov 11", status: "To File", amount: "₹42.5L Sales" },
    { title: "GSTR-3B (Summary)", period: "Oct 2024", dueDate: "Nov 20", status: "To File", amount: "₹42,500 Liability" },
    { title: "TDS 26Q", period: "Q2 2024-25", dueDate: "Oct 31", status: "Filed", amount: "₹12,400 Deducted" },
];

export function ComplianceChecklist() {
    return (
        <div className="space-y-4">
            {obligations.map((item, i) => (
                <Card key={i} className="hover:bg-muted/30 transition-colors">
                    <CardHeader className="pb-2 pt-4">
                        <div className="flex justify-between items-start">
                            <div>
                                <CardTitle className="text-base font-semibold">{item.title}</CardTitle>
                                <p className="text-sm text-muted-foreground">{item.period}</p>
                            </div>
                            <StatusBadge status={item.status} />
                        </div>
                    </CardHeader>
                    <CardContent className="pb-2">
                        <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">Due: <span className="font-medium text-foreground">{item.dueDate}</span></span>
                            <span className="font-medium">{item.amount}</span>
                        </div>
                    </CardContent>
                    <CardFooter className="pt-2 pb-4 gap-2">
                        <Button variant="outline" size="sm" className="h-8 gap-2">
                            <UploadCloud className="h-3.5 w-3.5" /> Export JSON
                        </Button>
                        <Button variant="ghost" size="sm" className="h-8 gap-2">
                            <Download className="h-3.5 w-3.5" /> Summary
                        </Button>
                    </CardFooter>
                </Card>
            ))}
        </div>
    );
}

function StatusBadge({ status }: { status: string }) {
    if (status === 'Filed') return <Badge variant="secondary" className="bg-emerald-100 text-emerald-800 hover:bg-emerald-100">Filed</Badge>;
    if (status === 'Overdue') return <Badge variant="destructive">Overdue</Badge>;
    return <Badge variant="outline" className="border-amber-500 text-amber-600 bg-amber-50">To File</Badge>;
}
