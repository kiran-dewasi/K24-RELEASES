"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    MessageSquare, Phone, CheckCircle2, ArrowUpRight, ArrowDownLeft,
    AlertCircle, Loader2, Settings, MessageCircle, Users, Zap
} from "lucide-react";
import { useState, useEffect } from "react";
import { apiRequest } from "@/lib/api";

const CLOUD_API = "https://weare-production.up.railway.app";
import Link from "next/link";

interface UserStatus {
    id: number;
    full_name: string;
    whatsapp_number: string | null;
    is_whatsapp_verified: boolean;
    tenant_id: string;
    email: string;
}

interface BotStatus {
    whatsapp_connected: boolean;
    phone_number: string | null;
}

interface MessageStats {
    sent: number;
    received: number;
    total: number;
}

interface CustomerCount {
    total: number;
}

export function WhatsAppSettings() {
    const [loading, setLoading] = useState(true);
    const [userStatus, setUserStatus] = useState<UserStatus | null>(null);
    const [botStatus, setBotStatus] = useState<BotStatus>({ whatsapp_connected: false, phone_number: null });
    const [stats, setStats] = useState<MessageStats>({ sent: 0, received: 0, total: 0 });
    const [customerCount, setCustomerCount] = useState(0);

    useEffect(() => {
        fetchAll();
    }, []);

    const fetchAll = async () => {
        setLoading(true);
        try {
            const token = typeof window !== "undefined" ? localStorage.getItem("k24_token") : null;
            const meRes = await fetch(`${CLOUD_API}/api/auth/me`, {
                headers: {
                    "Content-Type": "application/json",
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
            });
            const userStatusData: UserStatus | null = meRes.ok ? await meRes.json() : null;

            const [botRes, statsRes, custRes] = await Promise.allSettled([
                apiRequest<BotStatus>("/api/baileys/status"),
                apiRequest<MessageStats>("/api/whatsapp/message-stats"),
                apiRequest<{ mappings: any[]; total: number }>("/api/whatsapp/customers"),
            ]);

            if (userStatusData) setUserStatus(userStatusData);
            if (botRes.status === "fulfilled") setBotStatus(botRes.value);
            if (statsRes.status === "fulfilled") setStats(statsRes.value);
            if (custRes.status === "fulfilled") setCustomerCount(custRes.value.total ?? 0);
        } catch (e) {
            console.error("Failed to fetch WhatsApp settings data", e);
        } finally {
            setLoading(false);
        }
    };

    const linkedNumber = userStatus?.whatsapp_number || null;
    const isLinked = !!linkedNumber;

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center py-20 text-muted-foreground gap-3">
                <Loader2 className="animate-spin h-8 w-8" />
                <p className="text-sm">Loading WhatsApp settings...</p>
            </div>
        );
    }

    return (
        <div className="space-y-6 max-w-2xl">

            {/* ── Main Status Card ──────────────────────────────── */}
            <Card className={`border-l-4 shadow-sm transition-colors ${isLinked ? "border-l-emerald-500 bg-emerald-50/30" : "border-l-amber-400 bg-amber-50/30"}`}>
                <CardHeader className="pb-3">
                    <CardTitle className="flex items-center justify-between text-base">
                        <span className="flex items-center gap-2">
                            <Phone className={`h-5 w-5 ${isLinked ? "text-emerald-600" : "text-amber-500"}`} />
                            Your WhatsApp Number
                        </span>
                        {isLinked ? (
                            <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200 gap-1.5 pl-1.5">
                                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse inline-block" />
                                Linked
                            </Badge>
                        ) : (
                            <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200 gap-1.5">
                                <AlertCircle className="h-3 w-3" />
                                Not Set
                            </Badge>
                        )}
                    </CardTitle>
                    <CardDescription>
                        This number identifies your account for receiving WhatsApp bills and messages.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {isLinked ? (
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center">
                                    <CheckCircle2 className="h-5 w-5" />
                                </div>
                                <div>
                                    <p className="font-mono text-lg font-bold text-foreground">{linkedNumber}</p>
                                    <p className="text-xs text-muted-foreground">Linked to tenant: {userStatus?.tenant_id}</p>
                                </div>
                            </div>
                            <Button variant="outline" size="sm" asChild>
                                <Link href="/settings?tab=general">
                                    <Settings className="h-3.5 w-3.5 mr-1.5" />
                                    Change in Preferences
                                </Link>
                            </Button>
                        </div>
                    ) : (
                        <div className="flex items-center justify-between">
                            <p className="text-sm text-muted-foreground">
                                Go to <strong>Preferences</strong> and add your mobile number to link WhatsApp.
                            </p>
                            <Button size="sm" asChild className="bg-emerald-600 hover:bg-emerald-700 text-white">
                                <Link href="/settings?tab=general">
                                    Set Number →
                                </Link>
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* ── Business Bot Status ───────────────────────────── */}
            <Card className={`border-l-4 shadow-sm ${botStatus.whatsapp_connected ? "border-l-blue-500" : "border-l-gray-300"}`}>
                <CardHeader className="pb-3">
                    <CardTitle className="flex items-center justify-between text-base">
                        <span className="flex items-center gap-2">
                            <Zap className="h-4 w-4 text-blue-600" />
                            Business Bot
                        </span>
                        {botStatus.whatsapp_connected ? (
                            <Badge className="bg-blue-50 text-blue-700 border-blue-200 gap-1.5 pl-1.5">
                                <span className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse inline-block" />
                                Active
                            </Badge>
                        ) : (
                            <Badge variant="outline" className="text-muted-foreground">Offline</Badge>
                        )}
                    </CardTitle>
                    <CardDescription>
                        The central K24 bot that reads incoming bills.
                        {botStatus.phone_number && (
                            <span className="font-mono ml-1 font-semibold">{botStatus.phone_number}</span>
                        )}
                    </CardDescription>
                </CardHeader>
                {!botStatus.whatsapp_connected && (
                    <CardContent>
                        <p className="text-xs text-muted-foreground bg-muted/40 p-3 rounded-md border">
                            💡 Start the <code className="font-mono text-xs bg-muted px-1 rounded">baileys-listener</code> service.
                            It will print a QR code in the terminal — scan it once.
                        </p>
                    </CardContent>
                )}
            </Card>

            {/* ── Real Message Stats ────────────────────────────── */}
            <div className="grid grid-cols-3 gap-4">
                <Card className="text-center p-4 shadow-sm hover:shadow-md transition-shadow">
                    <div className="flex flex-col items-center gap-2">
                        <div className="w-10 h-10 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center">
                            <ArrowDownLeft className="h-5 w-5" />
                        </div>
                        <p className="text-2xl font-bold text-foreground">{stats.received.toLocaleString()}</p>
                        <p className="text-xs text-muted-foreground font-medium">Messages Received</p>
                    </div>
                </Card>

                <Card className="text-center p-4 shadow-sm hover:shadow-md transition-shadow">
                    <div className="flex flex-col items-center gap-2">
                        <div className="w-10 h-10 rounded-full bg-violet-50 text-violet-600 flex items-center justify-center">
                            <ArrowUpRight className="h-5 w-5" />
                        </div>
                        <p className="text-2xl font-bold text-foreground">{stats.sent.toLocaleString()}</p>
                        <p className="text-xs text-muted-foreground font-medium">Messages Sent</p>
                    </div>
                </Card>

                <Card className="text-center p-4 shadow-sm hover:shadow-md transition-shadow">
                    <div className="flex flex-col items-center gap-2">
                        <div className="w-10 h-10 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center">
                            <MessageCircle className="h-5 w-5" />
                        </div>
                        <p className="text-2xl font-bold text-foreground">{stats.total.toLocaleString()}</p>
                        <p className="text-xs text-muted-foreground font-medium">Total</p>
                    </div>
                </Card>
            </div>

            {/* ── Customer Routing CTA ──────────────────────────── */}
            <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-100 shadow-sm">
                <CardHeader className="pb-3">
                    <div className="flex items-center gap-2">
                        <div className="bg-blue-100 text-blue-600 p-2 rounded-lg">
                            <Users className="h-4 w-4" />
                        </div>
                        <CardTitle className="text-base">Customer Phone Routing</CardTitle>
                    </div>
                    <CardDescription className="text-blue-900/70">
                        Map customer numbers so KITTU can auto-identify who sends a bill.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Users className="h-4 w-4" />
                            <span>
                                {customerCount > 0
                                    ? <><strong className="text-foreground">{customerCount}</strong> customers registered</>
                                    : "No customers registered yet"}
                            </span>
                        </div>
                        <Button className="bg-blue-600 hover:bg-blue-700 text-white shadow-md" size="sm" asChild>
                            <Link href="/settings/whatsapp">
                                Manage Customers →
                            </Link>
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
