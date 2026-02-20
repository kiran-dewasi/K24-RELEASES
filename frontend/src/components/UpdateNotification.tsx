'use client';

import { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { RefreshCw, Download, X } from 'lucide-react';

export function UpdateNotification() {
    const [status, setStatus] = useState<string>('');
    const [loading, setLoading] = useState(false);
    const [visible, setVisible] = useState(false);

    useEffect(() => {
        // Check on mount
        checkForUpdates();

        // Check every 1 hour
        const interval = setInterval(checkForUpdates, 3600000);
        return () => clearInterval(interval);
    }, []);

    async function checkForUpdates() {
        if (typeof window === 'undefined') return;
        // Only run in real Tauri environment (not browser dev mode)
        if (!('__TAURI__' in window)) return;
        try {
            const msg = await invoke<string>('check_updates');
            console.log("Update check:", msg);
            if (msg.startsWith('Update available')) {
                setStatus(msg);
                setVisible(true);
            }
        } catch (e) {
            // Silently ignore — command may not be registered in all builds
        }
    }

    async function install() {
        setLoading(true);
        try {
            const res = await invoke<string>('install_update');
            setStatus(res);
            if (res === 'Update installed') {
                alert("Update installed. The application will restart.");
                await invoke('restart_app');
            }
        } catch (e) {
            setStatus("Error: " + e);
        }
        setLoading(false);
    }

    if (!visible) return null;

    return (
        <div className="fixed bottom-4 right-4 bg-white/90 backdrop-blur border border-indigo-100 p-4 shadow-xl rounded-lg z-50 animate-in slide-in-from-bottom duration-300 max-w-sm">
            <div className="flex justify-between items-start mb-2">
                <h3 className="font-semibold text-indigo-950 flex items-center gap-2">
                    <RefreshCw className="w-4 h-4 text-indigo-500" />
                    Update Available
                </h3>
                <button onClick={() => setVisible(false)} className="text-gray-400 hover:text-gray-600">
                    <X className="w-4 h-4" />
                </button>
            </div>

            <p className="text-sm text-gray-600 mb-4">{status}</p>

            <div className="flex gap-2">
                <button onClick={install} disabled={loading} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-2 rounded-md text-sm font-medium flex items-center justify-center transition-colors disabled:opacity-50">
                    {loading ? <RefreshCw className="w-4 h-4 animate-spin mr-2" /> : <Download className="w-4 h-4 mr-2" />}
                    {loading ? 'Installing...' : 'Install Now'}
                </button>
            </div>
        </div>
    )
}
