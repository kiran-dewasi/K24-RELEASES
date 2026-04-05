"use client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001';

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, CheckCircle, ShieldAlert, FileText, RefreshCw, ArrowLeft, Download } from "lucide-react";
import { useRouter } from "next/navigation";
import { downloadReportFile } from "@/lib/fileDownload";

interface AuditIssue {
    type: string;
    severity: "Critical" | "High" | "Medium" | "Low";
    message: string;
    details: string;
}

interface AuditReport {
    status: string;
    score: number;
    issue_count: number;
    issues: AuditIssue[];
}

export default function AuditPage() {
    const router = useRouter();
    const [report, setReport] = useState<AuditReport | null>(null);
    const [loading, setLoading] = useState(true);
    const [exporting, setExporting] = useState(false);

    const fetchAudit = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${API_URL}/audit/run`, {
                headers: { "x-api-key": "k24-secret-key-123" }
            });
            const data = await res.json();
            setReport(data);
        } catch (error) {
            console.error("Audit failed", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAudit();
    }, []);

    const handleExportPDF = async () => {
        if (!report) return;
        setExporting(true);
        try {
            await downloadReportFile({
                slug: "audit",
                format: "pdf"
            });
        } catch (error: any) {
            console.error("Audit export failed", error);
        } finally {
            setExporting(false);
        }
    };

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case "Critical": return "bg-red-100 text-red-800 border-red-200";
            case "High": return "bg-orange-100 text-orange-800 border-orange-200";
            case "Medium": return "bg-yellow-100 text-yellow-800 border-yellow-200";
            default: return "bg-blue-100 text-blue-800 border-blue-200";
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 p-8">
            <div className="max-w-5xl mx-auto space-y-8">
                {/* Header */}
                <div className="flex justify-between items-center">
                    <div className="flex items-center gap-4">
                        <Button variant="ghost" size="icon" onClick={() => router.back()}>
                            <ArrowLeft className="h-5 w-5" />
                        </Button>
                        <div>
                            <h1 className="text-3xl font-bold tracking-tight">AI Auditor</h1>
                            <p className="text-muted-foreground">Continuous Compliance & Health Check</p>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <Button variant="outline" onClick={handleExportPDF} disabled={!report || exporting}>
                            <Download className="mr-2 h-4 w-4" />
                            {exporting ? "Exporting..." : "Export PDF"}
                        </Button>
                        <Button onClick={fetchAudit} disabled={loading}>
                            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                            Run Audit
                        </Button>
                    </div>
                </div>

                {/* Scorecard */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <Card className="md:col-span-1 bg-white border-l-4 border-l-blue-600">
                        <CardHeader>
                            <CardTitle className="text-sm font-medium text-muted-foreground">Audit Score</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="flex items-baseline gap-2">
                                <span className={`text-5xl font-bold ${(report?.score || 0) > 80 ? 'text-green-600' :
                                    (report?.score || 0) > 50 ? 'text-yellow-600' : 'text-red-600'
                                    }`}>
                                    {report?.score ?? "--"}
                                </span>
                                <span className="text-muted-foreground">/ 100</span>
                            </div>
                            <p className="text-sm mt-2 text-muted-foreground">
                                {(report?.score || 0) > 80 ? "Excellent Health" : "Needs Attention"}
                            </p>
                        </CardContent>
                    </Card>

                    <Card className="md:col-span-1">
                        <CardHeader>
                            <CardTitle className="text-sm font-medium text-muted-foreground">Issues Found</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-4xl font-bold text-gray-900">{report?.issue_count ?? 0}</div>
                            <p className="text-sm mt-2 text-muted-foreground">Across {report?.issues.length ? new Set(report.issues.map(i => i.type)).size : 0} categories</p>
                        </CardContent>
                    </Card>

                    <Card className="md:col-span-1">
                        <CardHeader>
                            <CardTitle className="text-sm font-medium text-muted-foreground">Status</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="flex items-center gap-2">
                                {report?.status === "clean" ? (
                                    <CheckCircle className="h-8 w-8 text-green-500" />
                                ) : (
                                    <ShieldAlert className="h-8 w-8 text-orange-500" />
                                )}
                                <span className="text-xl font-semibold capitalize">
                                    {report?.status ?? "Checking..."}
                                </span>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Issues List */}
                <Card>
                    <CardHeader>
                        <CardTitle>Detailed Findings</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {!report ? (
                            <div className="text-center py-12 text-muted-foreground">Loading audit data...</div>
                        ) : report.issues.length === 0 ? (
                            <div className="text-center py-12 flex flex-col items-center gap-4">
                                <CheckCircle className="h-12 w-12 text-green-500" />
                                <h3 className="text-lg font-medium">All Systems Nominal</h3>
                                <p className="text-muted-foreground">No compliance or data quality issues found.</p>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {report.issues.map((issue, idx) => (
                                    <div key={idx} className="flex items-start justify-between p-4 border rounded-lg hover:bg-gray-50 transition-colors">
                                        <div className="flex gap-4">
                                            <div className="mt-1">
                                                <AlertTriangle className={`h-5 w-5 ${issue.severity === 'Critical' ? 'text-red-500' : 'text-yellow-500'
                                                    }`} />
                                            </div>
                                            <div>
                                                <h4 className="font-semibold text-gray-900">{issue.message}</h4>
                                                <p className="text-sm text-muted-foreground mt-1">{issue.details}</p>
                                                <div className="flex gap-2 mt-2">
                                                    <Badge variant="outline" className="text-xs">
                                                        {issue.type}
                                                    </Badge>
                                                </div>
                                            </div>
                                        </div>
                                        <Badge className={`${getSeverityColor(issue.severity)}`}>
                                            {issue.severity}
                                        </Badge>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
