"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
    ShieldAlert,
    CalendarClock,
    Banknote,
    FileText,
    History,
    CheckCircle2,
    AlertTriangle,
    Download
} from "lucide-react";
import { downloadReportFile } from "@/lib/fileDownload";

interface AuditLog {
    id: number;
    entity_type: string;
    entity_id: string;
    user_id: string;
    action: string;
    timestamp: string;
    old_value: string | null;
    new_value: string | null;
    reason: string;
}

interface DashboardStats {
    high_value_count: number;
    backdated_count: number;
    weekend_count: number;
    pending_tds: number;
}

export default function AuditDashboard() {
    const [logs, setLogs] = useState<AuditLog[]>([]);
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [exporting, setExporting] = useState(false);
    const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const [logsRes, statsRes] = await Promise.all([
                fetch("https://weare-production.up.railway.app/compliance/audit-logs"),
                fetch("https://weare-production.up.railway.app/compliance/dashboard-stats")
            ]);

            const logsData = await logsRes.json();
            const statsData = await statsRes.json();

            setLogs(logsData);
            setStats(statsData);
        } catch (error) {
            console.error("Failed to fetch compliance data", error);
        } finally {
            setLoading(false);
        }
    };

    const handleExportPDF = async () => {
        setExporting(true);
        try {
            await downloadReportFile({
                slug: "audit-logs",
                format: "pdf"
            });
        } catch (error: any) {
            console.error("Audit export failed", error);
            // Optionally add a toast here
        } finally {
            setExporting(false);
        }
    };

    const formatDiff = (oldVal: string | null, newVal: string | null) => {
        if (!oldVal && !newVal) return "No changes";
        const oldObj = oldVal ? JSON.parse(oldVal) : {};
        const newObj = newVal ? JSON.parse(newVal) : {};

        return (
            <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                <div className="bg-red-50 p-2 rounded">
                    <strong className="text-red-700 block mb-1">Old Value</strong>
                    <pre className="whitespace-pre-wrap">{JSON.stringify(oldObj, null, 2)}</pre>
                </div>
                <div className="bg-green-50 p-2 rounded">
                    <strong className="text-green-700 block mb-1">New Value</strong>
                    <pre className="whitespace-pre-wrap">{JSON.stringify(newObj, null, 2)}</pre>
                </div>
            </div>
        );
    };

    return (
        <div className="min-h-screen bg-gray-100 p-8">
            <div className="max-w-7xl mx-auto space-y-6">
                <div className="flex justify-between items-center">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">Auditor Dashboard</h1>
                        <p className="text-gray-500">MCA Compliance & Forensic Audit Trail</p>
                    </div>
                    <div className="flex gap-2">
                        <Button onClick={handleExportPDF} disabled={exporting} className="bg-blue-600 hover:bg-blue-700">
                            <Download className="h-4 w-4 mr-2" />
                            {exporting ? "Exporting..." : "Export PDF"}
                        </Button>
                        <Button onClick={fetchData} variant="outline" disabled={loading}>Refresh Data</Button>
                    </div>
                </div>

                {/* Widgets */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <Card className="border-l-4 border-l-red-500">
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm font-medium">High Value (&gt;2L)</CardTitle>
                            <Banknote className="h-4 w-4 text-red-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{stats?.high_value_count || 0}</div>
                            <p className="text-xs text-muted-foreground">Cash transactions flagged</p>
                        </CardContent>
                    </Card>

                    <Card className="border-l-4 border-l-orange-500">
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm font-medium">Backdated Entries</CardTitle>
                            <History className="h-4 w-4 text-orange-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{stats?.backdated_count || 0}</div>
                            <p className="text-xs text-muted-foreground">Modified post-facto</p>
                        </CardContent>
                    </Card>

                    <Card className="border-l-4 border-l-yellow-500">
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm font-medium">Weekend Entries</CardTitle>
                            <CalendarClock className="h-4 w-4 text-yellow-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{stats?.weekend_count || 0}</div>
                            <p className="text-xs text-muted-foreground">Sat/Sun transactions</p>
                        </CardContent>
                    </Card>

                    <Card className="border-l-4 border-l-blue-500">
                        <CardHeader className="flex flex-row items-center justify-between pb-2">
                            <CardTitle className="text-sm font-medium">Pending TDS</CardTitle>
                            <FileText className="h-4 w-4 text-blue-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">₹{(stats?.pending_tds || 0).toLocaleString()}</div>
                            <p className="text-xs text-muted-foreground">Estimated liability</p>
                        </CardContent>
                    </Card>
                </div>

                {/* Audit Log Grid */}
                <Card>
                    <CardHeader>
                        <CardTitle>Immutable Audit Trail</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm text-left">
                                <thead className="text-xs text-gray-700 uppercase bg-gray-50">
                                    <tr>
                                        <th className="px-4 py-3">Timestamp</th>
                                        <th className="px-4 py-3">User</th>
                                        <th className="px-4 py-3">Action</th>
                                        <th className="px-4 py-3">Entity</th>
                                        <th className="px-4 py-3">Reason</th>
                                        <th className="px-4 py-3">Details</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {logs.map((log) => (
                                        <tr key={log.id} className="bg-white border-b hover:bg-gray-50">
                                            <td className="px-4 py-3 font-mono">
                                                {new Date(log.timestamp).toLocaleString()}
                                            </td>
                                            <td className="px-4 py-3 font-medium text-blue-600">
                                                {log.user_id}
                                            </td>
                                            <td className="px-4 py-3">
                                                <span className={`px-2 py-1 rounded-full text-xs font-bold ${log.action === 'CREATE' ? 'bg-green-100 text-green-800' :
                                                        log.action === 'UPDATE' ? 'bg-yellow-100 text-yellow-800' :
                                                            'bg-red-100 text-red-800'
                                                    }`}>
                                                    {log.action}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3">
                                                {log.entity_type} #{log.entity_id}
                                            </td>
                                            <td className="px-4 py-3 italic text-gray-500">
                                                "{log.reason}"
                                            </td>
                                            <td className="px-4 py-3">
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    onClick={() => setSelectedLog(log)}
                                                >
                                                    View Diff
                                                </Button>
                                            </td>
                                        </tr>
                                    ))}
                                    {logs.length === 0 && (
                                        <tr>
                                            <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                                                No audit logs found.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </CardContent>
                </Card>

                {/* Diff Modal */}
                {selectedLog && (
                    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                        <Card className="w-full max-w-4xl max-h-[90vh] overflow-y-auto">
                            <CardHeader className="flex flex-row items-center justify-between">
                                <CardTitle>Audit Log Details #{selectedLog.id}</CardTitle>
                                <Button variant="ghost" size="sm" onClick={() => setSelectedLog(null)}>Close</Button>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-2 gap-4 text-sm">
                                    <div>
                                        <span className="font-semibold">User:</span> {selectedLog.user_id}
                                    </div>
                                    <div>
                                        <span className="font-semibold">Timestamp:</span> {new Date(selectedLog.timestamp).toLocaleString()}
                                    </div>
                                    <div className="col-span-2">
                                        <span className="font-semibold">Reason:</span> {selectedLog.reason}
                                    </div>
                                </div>

                                <div className="border-t pt-4">
                                    <h3 className="font-semibold mb-2">Change History</h3>
                                    {formatDiff(selectedLog.old_value, selectedLog.new_value)}
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                )}
            </div>
        </div>
    );
}
