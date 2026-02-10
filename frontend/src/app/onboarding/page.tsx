"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { apiRequest } from "@/lib/api";
import {
    CheckCircle,
    ChevronRight,
    Smartphone,
    Database,
    Loader2,
    ShieldCheck,
    Zap,
    LayoutDashboard,
    AlertCircle
} from "lucide-react";

export default function OnboardingWizard() {
    const router = useRouter();
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);

    // Step 1: Tally
    const [tallyUrl, setTallyUrl] = useState("http://localhost:9000");
    const [tallyStatus, setTallyStatus] = useState<"idle" | "scanning" | "checking" | "connected" | "failed">("scanning");

    // Step 2: Sync
    const [syncProgress, setSyncProgress] = useState(0);
    const [syncStatus, setSyncStatus] = useState<"idle" | "syncing" | "completed" | "failed">("idle");

    // Step 3: AI
    const [apiKey, setApiKey] = useState("");
    const [aiStatus, setAiStatus] = useState<"idle" | "verifying" | "valid" | "invalid" | "skipped">("idle");

    const steps = [
        { id: 1, title: "Connect Tally", icon: Database },
        { id: 2, title: "Initial Sync", icon: Zap },
        { id: 3, title: "AI Setup", icon: Smartphone }, // Using Smartphone icon as placeholder for AI/Features
        { id: 4, title: "Ready", icon: CheckCircle }
    ];

    useEffect(() => {
        if (step === 1) {
            scanForTally();
        }
    }, [step]);

    const scanForTally = async () => {
        setTallyStatus("scanning");
        try {
            const res = await apiRequest("/api/setup/scan-tally");
            if (res.instances && res.instances.length > 0) {
                // Pick first found
                const foundUrl = res.instances[0].url;
                setTallyUrl(foundUrl);
                // Verify it specifically
                const health = await apiRequest("/api/health/tally");
                if (health.status === "online") {
                    setTallyStatus("connected");
                    await apiRequest("/setup/save", "POST", { tally_url: foundUrl });
                } else {
                    setTallyStatus("idle");
                }
            } else {
                setTallyStatus("idle"); // Not found, manual input
            }
        } catch (e) {
            setTallyStatus("idle");
        }
    };

    const checkTallyConnection = async () => {
        setTallyStatus("checking");
        try {
            // Using the health check endpoint
            const res = await apiRequest("/api/health/tally");
            if (res.status === "online") {
                setTallyStatus("connected");
                // Auto-save this URL setting
                await apiRequest("/setup/save", "POST", { tally_url: tallyUrl });
            } else {
                setTallyStatus("failed");
            }
        } catch (e) {
            console.error(e);
            setTallyStatus("failed");
        }
    };

    const startInitialSync = async () => {
        setSyncStatus("syncing");
        setSyncProgress(10);

        try {
            // Simulate progress for UX
            const interval = setInterval(() => {
                setSyncProgress(prev => Math.min(prev + 5, 90));
            }, 500);

            // Trigger actual sync
            await apiRequest("/api/sync/full", "POST"); // Assuming this endpoint exists based on sync engine

            clearInterval(interval);
            setSyncProgress(100);
            setSyncStatus("completed");
        } catch (e) {
            console.error(e);
            setSyncStatus("failed");
        }
    };

    const verifyAiKey = async () => {
        setAiStatus("verifying");
        try {
            const res = await apiRequest("/api/ai/verify-key", "POST", { api_key: apiKey });
            if (res.valid) {
                await apiRequest("/api/settings/save-api-key", "POST", { api_key: apiKey });
                setAiStatus("valid");
            } else {
                setAiStatus("invalid");
            }
        } catch (e) {
            setAiStatus("invalid");
        }
    };

    const handleNext = () => {
        if (step < 4) setStep(step + 1);
        else router.push("/dashboard");
    };

    return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4 font-sans">
            <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center [mask-image:linear-gradient(180deg,white,rgba(255,255,255,0))]"></div>

            <Card className="w-full max-w-3xl shadow-2xl border-0 overflow-hidden relative z-10">
                <div className="grid md:grid-cols-[250px_1fr] min-h-[500px]">
                    {/* Sidebar */}
                    <div className="bg-slate-900 text-white p-8 flex flex-col justify-between relative overflow-hidden">
                        <div className="absolute top-0 left-0 w-full h-full bg-blue-600/10 z-0"></div>
                        <div className="relative z-10">
                            <div className="flex items-center gap-2 mb-10">
                                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center font-bold">K</div>
                                <span className="text-xl font-bold tracking-tight">K24 Setup</span>
                            </div>

                            <div className="space-y-6">
                                {steps.map((s, idx) => (
                                    <div key={s.id} className={`flex items-center gap-3 ${step === s.id ? 'text-white' : 'text-slate-500'}`}>
                                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm border ${step === s.id ? 'bg-blue-600 border-blue-600' :
                                                step > s.id ? 'bg-green-500 border-green-500 text-white' : 'border-slate-700'
                                            }`}>
                                            {step > s.id ? <CheckCircle className="w-4 h-4" /> : s.id}
                                        </div>
                                        <span className={`font-medium ${step === s.id ? 'text-blue-200' : ''}`}>{s.title}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="text-xs text-slate-500 relative z-10">
                            Version 2.0.0
                        </div>
                    </div>

                    {/* Content */}
                    <CardContent className="p-10 flex flex-col justify-center bg-white">
                        <AnimatePresence mode="wait">
                            {/* STEP 1: TALLY */}
                            {step === 1 && (
                                <motion.div
                                    key="step1"
                                    initial={{ opacity: 0, x: 20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, x: -20 }}
                                    className="space-y-6"
                                >
                                    <div>
                                        <h2 className="text-2xl font-bold text-slate-900">Connect to Tally</h2>
                                        <p className="text-slate-500">Ensure Tally Prime is running and ODBC is enabled.</p>
                                    </div>

                                    <div className="space-y-4">
                                        <div className="space-y-2">
                                            <Label>Tally URL</Label>
                                            <div className="flex gap-2">
                                                <Input
                                                    value={tallyUrl}
                                                    onChange={(e) => setTallyUrl(e.target.value)}
                                                    className="flex-1"
                                                    disabled={tallyStatus === 'scanning'}
                                                />
                                                <Button
                                                    onClick={checkTallyConnection}
                                                    disabled={tallyStatus === 'checking' || tallyStatus === 'connected' || tallyStatus === 'scanning'}
                                                    variant={tallyStatus === 'connected' ? 'outline' : 'default'}
                                                    className={tallyStatus === 'connected' ? "border-green-500 text-green-600 bg-green-50" : ""}
                                                >
                                                    {(tallyStatus === 'checking' || tallyStatus === 'scanning') ? <Loader2 className="w-4 h-4 animate-spin" /> :
                                                        tallyStatus === 'connected' ? <CheckCircle className="w-4 h-4" /> : "Connect"}
                                                </Button>
                                            </div>
                                            {tallyStatus === 'scanning' && (
                                                <p className="text-sm text-blue-600 flex items-center gap-2">
                                                    <Loader2 className="w-3 h-3 animate-spin" /> Scanning for Tally...
                                                </p>
                                            )}
                                            {tallyStatus === 'connected' && (
                                                <p className="text-sm text-green-600 flex items-center gap-2">
                                                    <CheckCircle className="w-3 h-3" /> Connected successfully
                                                </p>
                                            )}
                                            {tallyStatus === 'failed' && (
                                                <p className="text-sm text-red-600 flex items-center gap-2">
                                                    <AlertCircle className="w-3 h-3" /> Connection failed. Check Tally config.
                                                </p>
                                            )}
                                        </div>
                                    </div>

                                    <div className="pt-4 flex justify-end">
                                        <Button
                                            onClick={handleNext}
                                            disabled={tallyStatus !== 'connected'}
                                            className="bg-slate-900 hover:bg-slate-800"
                                        >
                                            Next Step <ChevronRight className="w-4 h-4 ml-2" />
                                        </Button>
                                    </div>
                                </motion.div>
                            )}

                            {/* STEP 2: SYNC */}
                            {step === 2 && (
                                <motion.div
                                    key="step2"
                                    initial={{ opacity: 0, x: 20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, x: -20 }}
                                    className="space-y-6"
                                >
                                    <div>
                                        <h2 className="text-2xl font-bold text-slate-900">Initial Synchronization</h2>
                                        <p className="text-slate-500">Fetching your ledgers and recent vouchers.</p>
                                    </div>

                                    <div className="space-y-6 py-4">
                                        {syncStatus === 'idle' && (
                                            <div className="bg-blue-50 p-6 rounded-xl border border-blue-100 text-center">
                                                <Database className="w-12 h-12 text-blue-500 mx-auto mb-3" />
                                                <p className="text-sm text-blue-700 font-medium mb-4">Ready to fetch data from Tally</p>
                                                <Button onClick={startInitialSync} size="lg" className="w-full">
                                                    Start Sync
                                                </Button>
                                            </div>
                                        )}

                                        {syncStatus === 'syncing' && (
                                            <div className="space-y-2">
                                                <div className="flex justify-between text-sm font-medium">
                                                    <span>Syncing data...</span>
                                                    <span>{syncProgress}%</span>
                                                </div>
                                                <Progress value={syncProgress} className="h-2" />
                                                <p className="text-xs text-muted-foreground text-center pt-2">This may take a minute...</p>
                                            </div>
                                        )}

                                        {syncStatus === 'completed' && (
                                            <div className="bg-green-50 p-6 rounded-xl border border-green-100 text-center">
                                                <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
                                                <p className="text-green-700 font-bold">Sync Complete!</p>
                                                <p className="text-green-600 text-sm">Your data is now ready.</p>
                                            </div>
                                        )}
                                    </div>

                                    <div className="pt-4 flex justify-end">
                                        <Button
                                            onClick={handleNext}
                                            disabled={syncStatus !== 'completed'}
                                            className="bg-slate-900 hover:bg-slate-800"
                                        >
                                            Next Step <ChevronRight className="w-4 h-4 ml-2" />
                                        </Button>
                                    </div>
                                </motion.div>
                            )}

                            {/* STEP 3: AI SETUP */}
                            {step === 3 && (
                                <motion.div
                                    key="step3"
                                    initial={{ opacity: 0, x: 20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, x: -20 }}
                                    className="space-y-6"
                                >
                                    <div>
                                        <h2 className="text-2xl font-bold text-slate-900">Activate AI Assistant</h2>
                                        <p className="text-slate-500">Enter your Google Gemini API Key to enable Kittu.</p>
                                    </div>

                                    <div className="space-y-4">
                                        <Label>Gemini API Key</Label>
                                        <div className="flex gap-2">
                                            <Input
                                                type="password"
                                                value={apiKey}
                                                onChange={(e) => setApiKey(e.target.value)}
                                                placeholder="AIzaSy..."
                                            />
                                            <Button
                                                onClick={verifyAiKey}
                                                disabled={aiStatus === 'verifying' || !apiKey}
                                            >
                                                {aiStatus === 'verifying' ? <Loader2 className="w-4 h-4 animate-spin" /> : "Verify"}
                                            </Button>
                                        </div>
                                        {aiStatus === 'valid' && (
                                            <p className="text-sm text-green-600 flex items-center gap-2">
                                                <ShieldCheck className="w-3 h-3" /> Key verified and encrypted.
                                            </p>
                                        )}
                                        <p className="text-xs text-muted-foreground">
                                            Don't have a key? <a href="https://ai.google.dev" target="_blank" className="text-blue-500 underline">Get one for free</a>.
                                        </p>
                                    </div>

                                    <div className="pt-4 flex justify-between">
                                        <Button variant="ghost" onClick={() => { setAiStatus("skipped"); handleNext(); }}>
                                            Skip for now
                                        </Button>
                                        <Button
                                            onClick={handleNext}
                                            disabled={aiStatus !== 'valid'}
                                            className="bg-slate-900 hover:bg-slate-800"
                                        >
                                            Next Step <ChevronRight className="w-4 h-4 ml-2" />
                                        </Button>
                                    </div>
                                </motion.div>
                            )}

                            {/* STEP 4: READY */}
                            {step === 4 && (
                                <motion.div
                                    key="step4"
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    className="text-center space-y-6 py-8"
                                >
                                    <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                                        <CheckCircle className="w-10 h-10 text-green-600" />
                                    </div>

                                    <div>
                                        <h2 className="text-3xl font-bold text-slate-900 mb-2">You're All Set!</h2>
                                        <p className="text-slate-500 max-w-sm mx-auto">
                                            K24 Desktop is configured and ready to use. Your financial intelligence dashboard awaits.
                                        </p>
                                    </div>

                                    <Button
                                        size="lg"
                                        onClick={() => router.push("/dashboard")}
                                        className="bg-blue-600 hover:bg-blue-700 text-lg px-8 h-12 shadow-lg shadow-blue-200"
                                    >
                                        <LayoutDashboard className="w-5 h-5 mr-2" />
                                        Go to Dashboard
                                    </Button>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </CardContent>
                </div>
            </Card>
        </div>
    );
}
