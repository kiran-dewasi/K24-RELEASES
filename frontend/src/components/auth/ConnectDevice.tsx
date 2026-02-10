"use client";

import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { Loader2, Monitor, Globe, CheckCircle, ShieldCheck, Key, ArrowRight, ChevronRight, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { open } from "@tauri-apps/plugin-shell";
import { onOpenUrl } from "@tauri-apps/plugin-deep-link";
import { invoke } from "@tauri-apps/api/core";

// Helper to detect if running in Tauri
const isTauri = () => typeof window !== "undefined" && "__TAURI__" in window;

interface ConnectDeviceProps {
    onAuthenticated: () => void;
}

export default function ConnectDevice({ onAuthenticated }: ConnectDeviceProps) {
    const [status, setStatus] = useState<"idle" | "waiting" | "validating" | "success" | "error">("idle");
    const [errorMsg, setErrorMsg] = useState("");
    const [manualKey, setManualKey] = useState("");
    const [showManual, setShowManual] = useState(false);
    const [mounted, setMounted] = useState(false);

    // Ensure we only render the portal on the client
    useEffect(() => {
        setMounted(true);
        // Prevent scrolling on body when locked
        document.body.style.overflow = 'hidden';
        return () => {
            document.body.style.overflow = 'unset';
        };
    }, []);

    useEffect(() => {
        let unlisten: (() => void) | undefined;

        const setupListener = async () => {
            if (!isTauri()) return;

            try {
                console.log("Setting up deep link listener...");
                unlisten = await onOpenUrl((urls) => {
                    console.log("Deep link received:", urls);
                    for (const url of urls) {
                        if (url.startsWith("k24://auth/callback")) {
                            handleCallback(url);
                        }
                    }
                });
            } catch (e) {
                console.error("Deep link listener error:", e);
            }
        };

        setupListener();

        return () => {
            if (unlisten) unlisten();
        };
    }, []);

    const handleCallback = async (url: string) => {
        try {
            setStatus("validating");
            const urlObj = new URL(url);
            const licenseKey = urlObj.searchParams.get("license_key");
            const userId = urlObj.searchParams.get("user_id");

            if (!licenseKey || !userId) {
                throw new Error("Invalid callback parameters");
            }

            await activateLicense(licenseKey, userId);

        } catch (e: any) {
            setStatus("error");
            setErrorMsg(e.message);
        }
    };

    const activateLicense = async (licenseKey: string, userId: string = "manual-user") => {
        try {
            setStatus("validating");
            const deviceId = localStorage.getItem("k24_device_id") || "manual-device";

            // Get dynamic port
            const backendPort = sessionStorage.getItem("k24_backend_port") || "8001";
            const backendUrl = `http://localhost:${backendPort}`;

            const response = await fetch(`${backendUrl}/api/devices/activate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    license_key: licenseKey,
                    device_id: deviceId
                })
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || "Activation failed locally");
            }

            const data = await response.json();
            const finalUserId = data.user_id || userId;

            localStorage.setItem("k24_license_key", licenseKey);
            localStorage.setItem("k24_user_id", finalUserId);

            setStatus("success");
            setTimeout(() => {
                onAuthenticated();
            }, 2000);

        } catch (e: any) {
            setStatus("error");
            setErrorMsg(e.message);
        }
    };

    const handleManualSubmit = () => {
        if (!manualKey) {
            setErrorMsg("Please enter a valid license key");
            return;
        }
        activateLicense(manualKey.trim());
    };

    const startConnection = async () => {
        setStatus("waiting");
        setErrorMsg("");

        try {
            // Get backend info (including dynamic port)
            let backendPort = "8001"; // Default for tests
            if (isTauri()) {
                const backendInfo: any = await invoke('start_backend');
                backendPort = backendInfo.port;
            }

            let deviceId = localStorage.getItem("k24_device_id");
            if (!deviceId) {
                deviceId = crypto.randomUUID();
                localStorage.setItem("k24_device_id", deviceId);
            }

            const appVersion = "1.0.1";
            const baseUrl = process.env.NEXT_PUBLIC_APP_URL || "https://k24.ai";
            const authUrl = `${baseUrl}/auth/desktop?device_id=${deviceId}&app_version=${appVersion}&port=${backendPort}`;

            // Store port for later use
            sessionStorage.setItem("k24_backend_port", String(backendPort));

            if (isTauri()) {
                // Explicitly import open from tauri/shell for v2
                const { open } = await import("@tauri-apps/plugin-shell");
                await open(authUrl);
            } else {
                window.open(authUrl, "_blank");
            }

            // Also set it for manual copy
            setManualKey(authUrl);

        } catch (e: any) {
            console.error(e);
            setStatus("error");
            setErrorMsg("Could not open browser. Please check your connection.");
        }
    };

    // The Content Component
    const Content = () => (
        <div className="fixed inset-0 z-[99999] flex items-center justify-center bg-[#0f172a] text-white">
            {/* Ambient Background */}
            <div className="absolute inset-0 overflow-hidden">
                <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] rounded-full bg-indigo-600/20 blur-[120px] animate-pulse-slow" />
                <div className="absolute bottom-[-20%] right-[-10%] w-[60%] h-[60%] rounded-full bg-cyan-600/10 blur-[120px]" />
                <div className="absolute inset-0 bg-[url('/grid-pattern.svg')] opacity-[0.03]" />
            </div>

            <div className="relative z-10 w-full max-w-5xl h-[600px] flex rounded-3xl overflow-hidden shadow-2xl border border-white/5 bg-black/40 backdrop-blur-xl ring-1 ring-white/10 m-4">

                {/* Left Side: Visuals & Branding */}
                <div className="hidden lg:flex w-5/12 relative flex-col justify-between p-12 bg-gradient-to-br from-indigo-950/50 to-slate-900/50">
                    <div className="absolute inset-0 bg-[linear-gradient(to_bottom,transparent,rgba(0,0,0,0.8))]" />

                    <div className="relative z-10">
                        <div className="h-10 w-10 bg-indigo-500 rounded-lg flex items-center justify-center mb-6 shadow-lg shadow-indigo-500/20">
                            <Monitor className="h-6 w-6 text-white" />
                        </div>
                        <h1 className="text-3xl font-bold tracking-tight text-white mb-2">
                            K24 Enterprise
                        </h1>
                        <p className="text-indigo-200/80 font-light">
                            Intelligent Business Operating System
                        </p>
                    </div>

                    <div className="relative z-10 space-y-6">
                        <div className="flex items-start gap-4 p-4 rounded-xl bg-white/5 border border-white/5 backdrop-blur-sm">
                            <ShieldCheck className="h-5 w-5 text-emerald-400 mt-1" />
                            <div>
                                <h3 className="text-sm font-semibold text-white">Bank-Grade Security</h3>
                                <p className="text-xs text-slate-400 mt-1">End-to-end encryption for all your financial data and Tally sync.</p>
                            </div>
                        </div>
                        <div className="flex items-start gap-4 p-4 rounded-xl bg-white/5 border border-white/5 backdrop-blur-sm">
                            <Globe className="h-5 w-5 text-cyan-400 mt-1" />
                            <div>
                                <h3 className="text-sm font-semibold text-white">Global Access</h3>
                                <p className="text-xs text-slate-400 mt-1">Manage your business from anywhere, on any authorized device.</p>
                            </div>
                        </div>
                    </div>

                    <div className="relative z-10 text-xs text-slate-500 font-mono">
                        Build v1.0.1 • Guaranteed Stable
                    </div>
                </div>

                {/* Right Side: Action Area */}
                <div className="flex-1 p-12 flex flex-col justify-center bg-white/5 relative">
                    {/* Success Overlay */}
                    {status === "success" && (
                        <div className="absolute inset-0 z-20 bg-emerald-950/90 backdrop-blur-sm flex items-center justify-center flex-col animate-in fade-in duration-500">
                            <div className="h-20 w-20 bg-emerald-500 rounded-full flex items-center justify-center shadow-lg shadow-emerald-500/30 mb-6 animate-bounce">
                                <CheckCircle className="h-10 w-10 text-white" />
                            </div>
                            <h2 className="text-2xl font-bold text-white mb-2">Device Authorized</h2>
                            <p className="text-emerald-200">Starting secure session...</p>
                        </div>
                    )}

                    <div className="max-w-md mx-auto w-full space-y-8">
                        <div className="text-center lg:text-left">
                            <h2 className="text-2xl font-bold text-white mb-2">
                                {showManual ? "Enter License Key" : "Connect Device"}
                            </h2>
                            <p className="text-slate-400 text-sm">
                                {showManual
                                    ? "Please enter the product key provided by your administrator."
                                    : "Authorize this computer to access your organization's data."}
                            </p>
                        </div>

                        {status === "error" && (
                            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-3 text-red-200 text-sm animate-in shake">
                                <span className="h-2 w-2 rounded-full bg-red-500 shrink-0" />
                                {errorMsg}
                            </div>
                        )}

                        {!showManual ? (
                            <div className="space-y-6">
                                <Button
                                    onClick={startConnection}
                                    disabled={status === "waiting"}
                                    className="w-full h-14 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-base rounded-xl shadow-lg shadow-indigo-900/50 transition-all flex items-center justify-center gap-2 group"
                                >
                                    {status === "waiting" ? <Loader2 className="animate-spin" /> : <Globe className="h-5 w-5" />}
                                    {status === "waiting" ? "Waiting for Browser..." : "Authenticate via Browser"}
                                    {!status && <ArrowRight className="h-4 w-4 opacity-50 group-hover:translate-x-1 transition-transform" />}
                                </Button>

                                {status === "waiting" && manualKey.startsWith("http") && (
                                    <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-2 animate-in fade-in slide-in-from-top-2">
                                        <p className="text-xs text-slate-400">Browser didn't open? Copy this link:</p>
                                        <div className="flex gap-2">
                                            <input
                                                readOnly
                                                value={manualKey}
                                                className="flex-1 bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-xs font-mono text-indigo-300 outline-none select-all"
                                                onClick={(e) => e.currentTarget.select()}
                                            />
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                className="h-auto bg-white/5 border-white/10 hover:bg-white/10 text-white"
                                                onClick={() => navigator.clipboard.writeText(manualKey)}
                                            >
                                                Copy
                                            </Button>
                                        </div>
                                    </div>
                                )}

                                <div className="relative">
                                    <div className="absolute inset-0 flex items-center">
                                        <span className="w-full border-t border-white/10" />
                                    </div>
                                    <div className="relative flex justify-center text-xs uppercase">
                                        <span className="bg-[#0f172a] px-2 text-slate-500">Or manually</span>
                                    </div>
                                </div>

                                <Button
                                    variant="ghost"
                                    onClick={() => setShowManual(true)}
                                    className="w-full h-12 border border-white/10 hover:bg-white/5 text-slate-300 rounded-xl flex items-center justify-center gap-2"
                                >
                                    <Key className="h-4 w-4" />
                                    I have a license key
                                </Button>
                            </div>
                        ) : (
                            <div className="space-y-6 animate-in slide-in-from-right duration-300">
                                <div className="space-y-2">
                                    <div className="relative group">
                                        <Key className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-500 group-focus-within:text-indigo-400 transition-colors" />
                                        <input
                                            type="text"
                                            className="w-full bg-black/20 border border-white/10 focus:border-indigo-500/50 rounded-xl py-4 pl-12 pr-4 text-white placeholder:text-slate-600 outline-none transition-all font-mono tracking-wider"
                                            placeholder="XXXX-XXXX-XXXX-XXXX"
                                            value={manualKey}
                                            onChange={(e) => setManualKey(e.target.value)}
                                            autoFocus
                                        />
                                    </div>
                                </div>
                                <div className="flex gap-3">
                                    <Button
                                        variant="ghost"
                                        onClick={() => setShowManual(false)}
                                        className="h-12 px-6 text-slate-400 hover:text-white hover:bg-white/5 rounded-xl border border-transparent hover:border-white/10"
                                    >
                                        Back
                                    </Button>
                                    <Button
                                        onClick={handleManualSubmit}
                                        disabled={status === "validating"}
                                        className="flex-1 h-12 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl shadow-lg shadow-indigo-900/50"
                                    >
                                        {status === "validating" ? <Loader2 className="animate-spin" /> : "Verify License"}
                                    </Button>
                                </div>
                            </div>
                        )}

                        <div className="flex items-center justify-center gap-2 text-xs text-slate-600 mt-8">
                            <Lock className="h-3 w-3" />
                            <span>Protected by K24 Secure Guard</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );

    if (!mounted) return null;

    // Portal to body ensures it covers absolutely everything
    return createPortal(<Content />, document.body);
}
