"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { RefreshCw, QrCode, Phone, CheckCircle, Smartphone, AlertCircle, Link as LinkIcon, ExternalLink, Loader2 } from "lucide-react";
import { useState, useEffect } from "react";
import { apiClient } from "@/lib/api-config";

interface BotStatus {
    whatsapp_connected: boolean;
    phone_number: string | null;
    qr_code?: string | null;
}

interface UserStatus {
    id: number;
    username: string;
    whatsapp_number: string | null;
    is_whatsapp_verified: boolean;
    tenant_id: string;
}

export function WhatsAppSettings() {
    // State management
    const [loading, setLoading] = useState(true);
    const [botStatus, setBotStatus] = useState<BotStatus>({ whatsapp_connected: false, phone_number: null });
    const [userStatus, setUserStatus] = useState<UserStatus | null>(null);

    // Async Action States
    const [generatingQR, setGeneratingQR] = useState(false);
    const [generatingPairCode, setGeneratingPairCode] = useState(false);
    const [qrData, setQrData] = useState<string | null>(null);
    const [pairCode, setPairCode] = useState<string | null>(null);
    const [instructions, setInstructions] = useState<string | null>(null);

    // Initial Data Fetch
    useEffect(() => {
        fetchStatus();
    }, []);

    const fetchStatus = async () => {
        setLoading(true);
        try {
            // 1. Fetch Bot/Business Status
            const botRes = await apiClient("/api/baileys/status");
            if (botRes.ok) {
                setBotStatus(await botRes.json());
            }

            // 2. Fetch User/Personal Status
            const userRes = await apiClient("/api/auth/me");
            if (userRes.ok) {
                setUserStatus(await userRes.json());
            }
        } catch (error) {
            console.error("Failed to fetch WhatsApp status:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleGenerateQR = async () => {
        // Business Bot QR generation usually requires Baileys interaction
        // For MVP, we point them to the console or assume auto-start
        alert("To link the Business Bot, please restart the 'baileys-listener' service. It will print the QR code in the terminal.");
    };

    const handleGeneratePairCode = async () => {
        setGeneratingPairCode(true);
        setPairCode(null);
        setInstructions(null);

        try {
            const res = await apiClient("/api/whatsapp/generate-code", {
                method: "POST"
            });

            if (res.ok) {
                const data = await res.json();
                setPairCode(data.code);
                setInstructions(data.instructions);
            } else {
                alert("Failed to generate code.");
            }
        } catch (error) {
            console.error("Error generating code:", error);
            alert("Error connecting to server.");
        } finally {
            setGeneratingPairCode(false);
        }
    };

    const handleUnlinkUser = async () => {
        if (!confirm("Are you sure you want to unlink your personal WhatsApp? You will stop receiving alerts.")) return;
        // TODO: Add unlink endpoint if needed, or just warn user
        alert("Unlinking requires admin support in this Beta version.");
    };

    if (loading) {
        return <div className="p-12 text-center text-gray-500 flex flex-col items-center">
            <Loader2 className="animate-spin mb-2" />
            Checking WhatsApp connectivity...
        </div>;
    }

    return (
        <div className="space-y-6">

            {/* Section 1: Bot Connection Status */}
            <Card className={`border-l-4 shadow-sm ${botStatus.whatsapp_connected ? 'border-l-emerald-500' : 'border-l-rose-500'}`}>
                <CardHeader className="pb-3">
                    <CardTitle className="flex items-center justify-between text-base">
                        <span className="flex items-center gap-2">
                            <Smartphone className={`h-4 w-4 ${botStatus.whatsapp_connected ? 'text-emerald-600' : 'text-rose-600'}`} />
                            Bot Connection Status
                        </span>
                        {botStatus.whatsapp_connected ? (
                            <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200 gap-1 pl-1">
                                <span className="h-1.5 w-1.5 rounded-full bg-emerald-600 animate-pulse" />
                                Connected
                            </Badge>
                        ) : (
                            <Badge variant="outline" className="bg-rose-50 text-rose-700 border-rose-200">Disconnected</Badge>
                        )}
                    </CardTitle>
                    <CardDescription className="text-xs">
                        The central WhatsApp bot that sends notifications and manages conversations.
                        {botStatus.phone_number && <span className="font-mono ml-1 font-semibold">({botStatus.phone_number})</span>}
                    </CardDescription>
                </CardHeader>
            </Card>

            {/* Section 2: Link Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

                {/* Card A: Business WhatsApp */}
                <Card className="flex flex-col h-full bg-white shadow-sm hover:border-primary/50 transition-colors">
                    <CardHeader className="pb-4">
                        <div className="flex justify-between items-start mb-2">
                            <div className="bg-blue-50 p-2 rounded-lg">
                                <QrCode className="h-5 w-5 text-blue-600" />
                            </div>
                            <Badge variant="secondary" className="font-normal text-muted-foreground">Business</Badge>
                        </div>
                        <CardTitle className="text-lg">Link Business Number</CardTitle>
                        <CardDescription>
                            Connect the phone number that K24 will use to send messages to your team.
                        </CardDescription>
                    </CardHeader>

                    <CardContent className="flex-1 space-y-4">
                        {/* Status Area */}
                        <div className="p-3 bg-muted/40 rounded-md border text-sm flex items-center gap-3">
                            <div className={`h-2 w-2 rounded-full ${botStatus.whatsapp_connected ? 'bg-emerald-500' : 'bg-gray-300'}`} />
                            <span className="text-muted-foreground font-medium">
                                {botStatus.whatsapp_connected ? `Linked: ${botStatus.phone_number}` : "Not Linked"}
                            </span>
                        </div>

                        <div className="mt-auto pt-2">
                            {!botStatus.whatsapp_connected ? (
                                <Button
                                    className="w-full gap-2"
                                    onClick={handleGenerateQR}
                                    disabled={generatingQR}
                                >
                                    {generatingQR ? <RefreshCw className="h-4 w-4 animate-spin" /> : <QrCode className="h-4 w-4" />}
                                    Generate QR Code
                                </Button>
                            ) : (
                                <Button variant="outline" className="w-full text-destructive hover:text-destructive border-destructive/20 gap-2" disabled>
                                    Disconnect Bot (Admin Only)
                                </Button>
                            )}
                            <p className="text-[10px] text-center mt-3 text-muted-foreground">
                                Scan with WhatsApp (Menu {'>'} Linked Devices)
                            </p>
                        </div>
                    </CardContent>
                </Card>

                {/* Card B: Personal WhatsApp */}
                <Card className="flex flex-col h-full bg-white shadow-sm hover:border-primary/50 transition-colors">
                    <CardHeader className="pb-4">
                        <div className="flex justify-between items-start mb-2">
                            <div className="bg-purple-50 p-2 rounded-lg">
                                <Phone className="h-5 w-5 text-purple-600" />
                            </div>
                            <Badge variant="secondary" className="font-normal text-muted-foreground">Personal</Badge>
                        </div>
                        <CardTitle className="text-lg">Link Your Account</CardTitle>
                        <CardDescription>
                            Pair your personal WhatsApp to chat with KITTU and receive private alerts.
                        </CardDescription>
                    </CardHeader>

                    <CardContent className="flex-1 space-y-4">
                        {/* Status Area */}
                        <div className="p-3 bg-muted/40 rounded-md border text-sm flex items-center gap-3">
                            {userStatus?.is_whatsapp_verified ? <CheckCircle className="h-4 w-4 text-emerald-500" /> : <AlertCircle className="h-4 w-4 text-amber-500" />}
                            <span className="text-muted-foreground font-medium">
                                {userStatus?.is_whatsapp_verified ? `Linked: ${userStatus.whatsapp_number}` : "Not Linked to User"}
                            </span>
                        </div>

                        {/* Visual for Pairing Code */}
                        {pairCode && !userStatus?.is_whatsapp_verified && (
                            <div className="p-6 bg-purple-50 rounded-lg border border-purple-100 text-center space-y-2 animate-in fade-in zoom-in duration-300">
                                <span className="text-xs font-semibold text-purple-600 uppercase tracking-widest">Pairing Code</span>
                                <div className="text-4xl font-mono font-bold text-purple-900 tracking-wider select-all cursor-pointer bg-white/50 p-2 rounded border border-dashed border-purple-200">
                                    {pairCode}
                                </div>
                                <p className="text-[11px] text-purple-700 font-medium bg-purple-100/50 py-1 px-2 rounded-full inline-block">
                                    {instructions || "Send this code to the bot"}
                                </p>
                            </div>
                        )}

                        <div className="mt-auto pt-2">
                            {!userStatus?.is_whatsapp_verified ? (
                                <Button
                                    className="w-full gap-2 bg-purple-600 hover:bg-purple-700 text-white"
                                    onClick={handleGeneratePairCode}
                                    disabled={generatingPairCode}
                                >
                                    {generatingPairCode ? <RefreshCw className="h-4 w-4 animate-spin" /> : <LinkIcon className="h-4 w-4" />}
                                    Generate Pairing Code
                                </Button>
                            ) : (
                                <Button variant="outline" className="w-full gap-2" onClick={handleUnlinkUser}>
                                    Unlink Device
                                </Button>
                            )}
                            <div className="flex justify-center mt-3">
                                <a href="#" className="flex items-center text-[10px] text-muted-foreground hover:text-primary transition-colors gap-1">
                                    Read setup options <ExternalLink className="h-3 w-3" />
                                </a>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Section 3: Customer Routing */}
            <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-100 shadow-sm">
                <CardHeader className="pb-3">
                    <div className="flex items-center gap-2 mb-1">
                        <div className="bg-blue-100 p-2 rounded-lg text-blue-600">
                            <span className="font-bold">@</span>
                        </div>
                        <CardTitle className="text-lg">Customer Phone Routing</CardTitle>
                    </div>
                    <CardDescription className="text-blue-900/70">
                        Map customer phone numbers to their accounts. This allows KITTU to automatically identify who is sending a bill and route it to the correct ledger.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center justify-between">
                        <div className="text-sm text-muted-foreground">
                            <ul className="list-disc pl-5 space-y-1">
                                <li>Register multiple numbers per customer</li>
                                <li>Auto-detect sender identity</li>
                                <li>Route documents to correct ledger</li>
                            </ul>
                        </div>
                        <Button
                            className="bg-blue-600 hover:bg-blue-700 text-white shadow-md"
                            onClick={() => window.location.href = '/settings/whatsapp'}
                        >
                            Manage Customers &rarr;
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
