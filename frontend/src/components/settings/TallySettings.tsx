"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { API_CONFIG } from "@/lib/api-config";
import { Loader2, Zap, AlertTriangle } from "lucide-react";

export function TallySettings() {
    const [tallyUrl, setTallyUrl] = useState("http://localhost:9000");
    const [googleApiKey, setGoogleApiKey] = useState("");
    const [autoPostToTally, setAutoPostToTally] = useState(false);
    const [loading, setLoading] = useState(false);
    const [pageLoading, setPageLoading] = useState(true);

    useEffect(() => {
        async function fetchConfig() {
            try {
                const res = await fetch(`${API_CONFIG.BASE_URL}/setup/status`);
                if (res.ok) {
                    const data = await res.json();
                    setTallyUrl(data.tally_url || "http://localhost:9000");
                    setGoogleApiKey(data.google_api_key || "");
                    setAutoPostToTally(data.auto_post_to_tally || false);
                }
            } catch (error) {
                console.error("Failed to fetch settings", error);
            } finally {
                setPageLoading(false);
            }
        }
        fetchConfig();
    }, []);

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            const res = await fetch(`${API_CONFIG.BASE_URL}/setup/save`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    tally_url: tallyUrl,
                    google_api_key: googleApiKey,
                    auto_post_to_tally: autoPostToTally
                })
            });

            if (res.ok) {
                alert("Settings saved successfully.");
            } else {
                alert("Failed to save settings.");
            }
        } catch (error) {
            console.error("Failed to save", error);
            alert("Error saving settings.");
        } finally {
            setLoading(false);
        }
    };

    if (pageLoading) {
        return <div className="p-8">Loading configuration...</div>;
    }

    return (
        <form onSubmit={handleSave} className="space-y-6 max-w-2xl">
            <Card>
                <CardHeader>
                    <CardTitle>Core Configuration</CardTitle>
                    <CardDescription>
                        Configure essential connections for K24 Desktop.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="tallyUrl">Tally Connector URL</Label>
                        <Input
                            id="tallyUrl"
                            value={tallyUrl}
                            onChange={(e) => setTallyUrl(e.target.value)}
                            placeholder="http://localhost:9000"
                        />
                        <p className="text-xs text-muted-foreground">
                            Usually port 9000. Ensure Tally Prime is running with 'Enable ODBC' allowed.
                        </p>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="apiKey">Google Gemini API Key</Label>
                        <Input
                            id="apiKey"
                            type="password"
                            value={googleApiKey}
                            onChange={(e) => setGoogleApiKey(e.target.value)}
                            placeholder="AIzaSy..."
                        />
                        <p className="text-xs text-muted-foreground">
                            Required for Kittu AI features.
                        </p>
                    </div>
                </CardContent>
            </Card>

            {/* Auto-Execution Settings Card */}
            <Card className="border-amber-200 dark:border-amber-800">
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <Zap className="h-5 w-5 text-amber-500" />
                        <CardTitle>Auto-Execution</CardTitle>
                    </div>
                    <CardDescription>
                        Configure automatic bill processing and Tally posting.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
                        <div className="space-y-1">
                            <div className="flex items-center gap-2">
                                <Label htmlFor="autoPost" className="font-medium">
                                    Auto-Post High-Confidence Vouchers
                                </Label>
                            </div>
                            <p className="text-sm text-muted-foreground">
                                When confidence ≥ 95%, vouchers from WhatsApp bills will be automatically posted to Tally without review.
                            </p>
                        </div>
                        <Switch
                            id="autoPost"
                            checked={autoPostToTally}
                            onCheckedChange={setAutoPostToTally}
                        />
                    </div>

                    {autoPostToTally && (
                        <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-200">
                            <AlertTriangle className="h-5 w-5 mt-0.5 shrink-0" />
                            <div className="text-sm">
                                <p className="font-medium">Auto-posting enabled</p>
                                <p className="text-amber-700 dark:text-amber-300">
                                    High-confidence bills will be posted directly to Tally. Make sure Tally is running and connected.
                                </p>
                            </div>
                        </div>
                    )}

                    <div className="text-xs text-muted-foreground space-y-1 pt-2">
                        <p><strong>How it works:</strong></p>
                        <ul className="list-disc list-inside space-y-1 ml-2">
                            <li><span className="text-green-600">95%+ confidence</span> → Auto-post to Tally (no questions asked)</li>
                            <li><span className="text-amber-600">75-94% confidence</span> → Create draft, ask for review</li>
                            <li><span className="text-red-600">Below 75%</span> → Ask one clarification question</li>
                        </ul>
                    </div>
                </CardContent>
                <CardFooter className="flex justify-end border-t pt-4">
                    <Button type="submit" disabled={loading}>
                        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Save Configuration
                    </Button>
                </CardFooter>
            </Card>
        </form>
    );
}

