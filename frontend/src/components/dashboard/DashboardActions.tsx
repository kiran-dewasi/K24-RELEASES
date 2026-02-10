"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowRight, Mail, AlertTriangle, FileText, CheckCircle2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";

const actions: any[] = [];

export function DashboardActions() {
    return (
        <Card className="col-span-1 lg:col-span-3">
            <CardHeader>
                <CardTitle className="text-base font-semibold">Next Best Actions</CardTitle>
                <CardDescription>AI-recommended tasks to improve cashflow and compliance</CardDescription>
            </CardHeader>
            <CardContent>
                {actions.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {actions.map((action, i) => (
                            <div key={i} className="flex items-start gap-4 p-4 rounded-lg border bg-card/50 hover:bg-muted/50 transition-colors">
                                <div className={`p-2 rounded-md ${action.color}`}>
                                    <action.icon className="h-5 w-5" />
                                </div>
                                <div className="flex-1 space-y-1">
                                    <div className="flex items-center justify-between">
                                        <h4 className="font-medium text-sm text-foreground">{action.title}</h4>
                                        <Badge variant={action.priority === "High" ? "destructive" : "secondary"} className="text-[10px] h-5 px-1.5">
                                            {action.priority}
                                        </Badge>
                                    </div>
                                    <p className="text-xs text-muted-foreground">{action.description}</p>
                                    <Button variant="link" className="p-0 h-auto text-primary text-xs font-medium gap-1 mt-2">
                                        {action.cta} <ArrowRight className="h-3 w-3" />
                                    </Button>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="flex flex-col items-center justify-center py-8 text-center space-y-3">
                        <div className="bg-emerald-50 p-3 rounded-full">
                            <CheckCircle2 className="h-6 w-6 text-emerald-600" />
                        </div>
                        <div className="space-y-1">
                            <h4 className="font-medium text-sm">All Caught Up!</h4>
                            <p className="text-xs text-muted-foreground max-w-xs mx-auto">
                                You have no pending actions. Your business is running smoothly.
                            </p>
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
