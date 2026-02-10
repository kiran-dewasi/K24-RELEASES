"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, CheckCircle, AlertTriangle, FileText, Shield, Download } from "lucide-react";
import { API_CONFIG } from "@/lib/api-config";

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

export default function AuditReport() {
    const [loading, setLoading] = useState(false);
    const [report, setReport] = useState<AuditReport | null>(null);

    const runAudit = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${API_CONFIG.BASE_URL}/audit/run`, {
                headers: {
                    "x-api-key": "k24-secret-key-123"
                }
            });
            const data = await res.json();
            setReport(data);
        } catch (error) {
            console.error("Audit failed:", error);
            alert("Failed to run audit. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    // Auto-run on mount
    useEffect(() => {
        runAudit();
    }, []);

    const downloadMarkdown = () => {
        if (!report) return;

        let markdown = `# Compliance Audit Report\n`;
        markdown += `**Generated:** ${new Date().toLocaleString()}\n\n`;
        markdown += `**Health Score:** ${report.score}/100\n\n`;

        markdown += `## Summary\n\n`;
        const issues = report.issues || [];
        const criticalCount = issues.filter(i => i.severity === "Critical").length;
        const highCount = issues.filter(i => i.severity === "High").length;
        const mediumCount = issues.filter(i => i.severity === "Medium").length;
        const lowCount = issues.filter(i => i.severity === "Low").length;

        markdown += `- Critical Issues: ${criticalCount}\n`;
        markdown += `- High Priority: ${highCount}\n`;
        markdown += `- Medium Priority: ${mediumCount}\n`;
        markdown += `- Low Priority: ${lowCount}\n`;
        markdown += `- Total Issues: ${report.issue_count}\n\n`;

        if (report.issues && report.issues.length > 0) {
            markdown += `## Issues Found\n\n`;
            report.issues.forEach((issue, idx) => {
                markdown += `### ${idx + 1}. ${issue.message}\n`;
                markdown += `**Severity:** ${issue.severity}\n`;
                markdown += `**Type:** ${issue.type}\n`;
                markdown += `**Details:** ${issue.details}\n`;
                markdown += `\n`;
            });
        }

        const blob = new Blob([markdown], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit-report-${new Date().toISOString().split('T')[0]}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case "Critical": return "bg-red-100 text-red-800 border-red-300";
            case "High": return "bg-orange-100 text-orange-800 border-orange-300";
            case "Medium": return "bg-yellow-100 text-yellow-800 border-yellow-300";
            default: return "bg-blue-100 text-blue-800 border-blue-300";
        }
    };

    const getScoreColor = (score: number) => {
        if (score >= 80) return "text-green-600";
        if (score >= 60) return "text-yellow-600";
        return "text-red-600";
    };

    const criticalCount = report && report.issues ? report.issues.filter(i => i.severity === "Critical").length : 0;
    const highCount = report && report.issues ? report.issues.filter(i => i.severity === "High").length : 0;
    const warningCount = criticalCount + highCount;

    return (
        <div className="w-full">
            <Card className="border-2 border-[#E6E1D6]">
                <CardHeader className="bg-gradient-to-r from-[#F5F2EB] to-white">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <Shield className="h-6 w-6 text-[#D96C46]" />
                            <div>
                                <CardTitle className="text-2xl font-serif text-[#1A1A1A]">AI Compliance Auditor</CardTitle>
                                <CardDescription className="text-[#686868]">Real-time Financial Health Check</CardDescription>
                            </div>
                        </div>
                        <div className="flex gap-2">
                            <Button
                                onClick={runAudit}
                                disabled={loading}
                                className="bg-[#D96C46] hover:bg-[#C05A35] text-white transition-all hover:scale-105 active:scale-95"
                            >
                                {loading ? (
                                    <span className="flex items-center gap-2">
                                        <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                                        Scanning...
                                    </span>
                                ) : (
                                    <span className="flex items-center gap-2">
                                        <FileText className="h-4 w-4" />
                                        Run Audit Check
                                    </span>
                                )}
                            </Button>
                            {report && (
                                <Button
                                    onClick={downloadMarkdown}
                                    variant="outline"
                                    className="border-[#D96C46] text-[#D96C46] hover:bg-[#D96C46] hover:text-white transition-all hover:scale-105 active:scale-95"
                                >
                                    <Download className="h-4 w-4 mr-2" />
                                    Export Report
                                </Button>
                            )}
                        </div>
                    </div>
                </CardHeader>

                {report && (
                    <CardContent className="pt-6 space-y-6">
                        {/* Summary Card */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <Card className="border border-[#E6E1D6]">
                                <CardContent className="pt-4 text-center">
                                    <div className={`text-4xl font-bold ${getScoreColor(report.score)}`}>{report.score}</div>
                                    <div className="text-sm text-[#686868]">Health Score</div>
                                </CardContent>
                            </Card>
                            <Card className="border border-[#E6E1D6]">
                                <CardContent className="pt-4 text-center">
                                    <div className="text-3xl font-bold text-red-600">{criticalCount}</div>
                                    <div className="text-sm text-[#686868]">Critical Issues</div>
                                </CardContent>
                            </Card>
                            <Card className="border border-[#E6E1D6]">
                                <CardContent className="pt-4 text-center">
                                    <div className="text-3xl font-bold text-yellow-600">{highCount}</div>
                                    <div className="text-sm text-[#686868]">High Priority</div>
                                </CardContent>
                            </Card>
                        </div>

                        {/* Issues List */}
                        {(report.issues || []).length > 0 ? (
                            <div className="space-y-3">
                                <h3 className="font-serif text-lg font-medium text-[#282828]">Issues Found</h3>
                                {(report.issues || []).map((issue, idx) => (
                                    <Card key={idx} className={`border-l-4 ${getSeverityColor(issue.severity)} transition-all hover:shadow-md hover:-translate-y-0.5`}>
                                        <CardContent className="pt-4">
                                            <div className="flex items-start gap-3">
                                                {issue.severity === "Critical" ? (
                                                    <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
                                                ) : issue.severity === "High" ? (
                                                    <AlertTriangle className="h-5 w-5 text-orange-600 mt-0.5" />
                                                ) : (
                                                    <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5" />
                                                )}
                                                <div className="flex-1">
                                                    <div className="flex items-center justify-between mb-1">
                                                        <h4 className="font-medium text-[#282828]">{issue.message}</h4>
                                                        <Badge variant="outline" className="text-xs">
                                                            {issue.severity}
                                                        </Badge>
                                                    </div>
                                                    <p className="text-sm text-[#686868] mb-2">{issue.details}</p>
                                                    <Badge variant="secondary" className="text-xs">
                                                        {issue.type}
                                                    </Badge>
                                                </div>
                                            </div>
                                        </CardContent>
                                    </Card>
                                ))}
                            </div>
                        ) : (
                            <Card className="border border-green-200 bg-green-50">
                                <CardContent className="pt-4">
                                    <div className="flex items-center gap-3">
                                        <CheckCircle className="h-6 w-6 text-green-600" />
                                        <div>
                                            <h4 className="font-medium text-green-900">All Clear!</h4>
                                            <p className="text-sm text-green-700">No compliance issues found. Your books look good.</p>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        )}

                        <div className="text-xs text-[#888888] pt-2 border-t">
                            Report generated on {new Date().toLocaleString()}
                        </div>
                    </CardContent>
                )}
            </Card>
        </div>
    );
}
