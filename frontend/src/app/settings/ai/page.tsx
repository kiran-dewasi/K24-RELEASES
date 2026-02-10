'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { apiRequest } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, XCircle, Loader2, Key } from 'lucide-react';

export default function AISettingsPage() {
    const [apiKey, setApiKey] = useState('');
    const [isVerifying, setIsVerifying] = useState(false);
    const [hasKey, setHasKey] = useState<boolean | null>(null);

    useEffect(() => {
        checkExistingKey();
    }, []);

    const checkExistingKey = async () => {
        try {
            const res = await apiRequest<{ has_key: boolean }>('/api/settings/has-api-key');
            setHasKey(res.has_key);
        } catch (e) {
            console.error("Failed to check key:", e);
        }
    };

    const verifyAndSave = async () => {
        if (!apiKey) return;

        setIsVerifying(true);

        try {
            // 1. Verify
            const verifyRes = await apiRequest<{ valid: boolean; error?: string }>('/api/ai/verify-key', 'POST', {
                api_key: apiKey
            });

            if (verifyRes.valid) {
                // 2. Save (backend encrypts it)
                await apiRequest('/api/settings/save-api-key', 'POST', {
                    api_key: apiKey
                });

                setHasKey(true);
                setApiKey(''); // Clear input for security
                alert('API Key Verified & Saved Securely!');
            } else {
                alert(`Invalid API Key: ${verifyRes.error || 'Generative AI rejected the key'}`);
            }
        } catch (error: any) {
            alert(`Error: ${error.message || 'Verification failed'}`);
        } finally {
            setIsVerifying(false);
        }
    };

    return (
        <div className="container max-w-2xl py-8">
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                            <Key className="h-6 w-6 text-primary" />
                            <CardTitle>AI Features Configuration</CardTitle>
                        </div>
                        {hasKey !== null && (
                            hasKey ?
                                <Badge variant="default" className="bg-green-600"><CheckCircle2 className="w-3 h-3 mr-1" /> Active</Badge> :
                                <Badge variant="destructive"><XCircle className="w-3 h-3 mr-1" /> Not Configured</Badge>
                        )}
                    </div>
                    <CardDescription>
                        Configure your Gemini API key to enable KITTU, the AI financial assistant.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">

                    <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg text-sm mb-6">
                        <h3 className="font-semibold mb-2 flex items-center">
                            <span className="text-xl mr-2">🔒</span> Security Guarantee
                        </h3>
                        <ul className="list-disc ml-5 space-y-1 text-muted-foreground">
                            <li>Your API Key is <strong>encrypted</strong> using a hardware-bound key before storage.</li>
                            <li>The key never leaves this machine in plain text.</li>
                            <li>Only K24 application can decrypt and use it.</li>
                        </ul>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium">Gemini API Key</label>
                        <div className="flex space-x-2">
                            <Input
                                type="password"
                                value={apiKey}
                                onChange={(e) => setApiKey(e.target.value)}
                                placeholder={hasKey ? "•••••••••••••••• (Key Configured)" : "Paste your API Key here"}
                                className="font-mono"
                            />
                            <Button onClick={verifyAndSave} disabled={isVerifying || !apiKey}>
                                {isVerifying && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                                {hasKey ? 'Update Key' : 'Verify & Save'}
                            </Button>
                        </div>
                        <p className="text-xs text-muted-foreground mt-2">
                            Don't have a key? Get one for free at <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer" className="text-primary hover:underline">Google AI Studio</a>.
                        </p>
                    </div>

                </CardContent>
            </Card>
        </div>
    );
}
