"use client";

import { useRouter } from "next/navigation";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, CheckCircle2, RefreshCw, Bell } from "lucide-react";
import { useState, useEffect } from "react";
import { API_CONFIG, apiClient } from "@/lib/api-config";

// Map routes to titles and subtitles
const PAGE_TITLES: Record<string, { title: string; subtitle?: string }> = {
    "/": { title: "Dashboard", subtitle: "Financial Overview" },
    "/chat": { title: "KITTU AI", subtitle: "Your Financial Assistant" },
    "/daybook": { title: "Daybook", subtitle: "Daily Transactions" },
    "/invoices": { title: "Invoices & Operations", subtitle: "Manage Sales & Purchases" },
    "/reports": { title: "Reports", subtitle: "Business Intelligence" },
    "/compliance": { title: "Compliance", subtitle: "GST & Filing Status" },
    "/settings": { title: "Settings", subtitle: "Preferences & Configurations" },
};

export default function Navbar() {
    const pathname = usePathname();
    const router = useRouter();
    const [searchQuery, setSearchQuery] = useState("");
    const [isSyncing, setIsSyncing] = useState(false);
    const [showSuccess, setShowSuccess] = useState(false);
    const [syncHealth, setSyncHealth] = useState<{ connected: boolean; lastSync: string | null }>({ connected: false, lastSync: null });

    // Search State
    interface SearchResult {
        ledgers: any[];
        vouchers: any[];
        items: any[];
    }
    const [results, setResults] = useState<SearchResult | null>(null);
    const [isOpen, setIsOpen] = useState(false);

    // Debounced Search
    useEffect(() => {
        const timer = setTimeout(async () => {
            if (searchQuery.length > 2) {
                try {
                    const res = await apiClient(`/api/search/global?q=${encodeURIComponent(searchQuery)}`);
                    if (res.ok) {
                        const data = await res.json();
                        setResults(data);
                        setIsOpen(true);
                    }
                } catch (e) {
                    console.error("Search failed", e);
                }
            } else {
                setResults(null);
                setIsOpen(false);
            }
        }, 300);
        return () => clearTimeout(timer);
    }, [searchQuery]);

    // Determine Title based on current path
    let currentPathConfig = PAGE_TITLES[pathname];

    // Handle dynamic routes loosely (e.g. /reports/sales)
    if (!currentPathConfig) {
        if (pathname.startsWith("/reports/")) {
            currentPathConfig = { title: "Report Details", subtitle: "Deep Dive Analysis" };
        } else if (pathname.startsWith("/chat")) {
            currentPathConfig = { title: "KITTU AI", subtitle: "Conversation" };
        } else {
            currentPathConfig = { title: "K24.ai", subtitle: "Intelligent ERP" };
        }
    }

    // Poll sync status
    useEffect(() => {
        const checkHealth = async () => {
            try {
                // Check desktop backend health
                const res = await fetch(`${API_CONFIG.BASE_URL}/health`);

                if (res.ok) {
                    // Backend is online
                    const newStatus = {
                        connected: true,
                        lastSync: new Date().toISOString()
                    };
                    setSyncHealth(newStatus);
                    localStorage.setItem('k24_sync_status', JSON.stringify(newStatus));
                } else {
                    setSyncHealth({ connected: false, lastSync: null });
                }
            } catch (e) {
                // Only log in development to avoid console noise in production
                if (process.env.NODE_ENV === 'development') {
                    console.error("Health check failed:", e);
                }
                setSyncHealth({ connected: false, lastSync: null });
            }
        };

        const cached = localStorage.getItem('k24_sync_status');
        if (cached) {
            try { setSyncHealth(JSON.parse(cached)); } catch (e) { }
        }

        checkHealth();
        const interval = setInterval(checkHealth, 30000);
        return () => clearInterval(interval);
    }, []);

    const handleSync = async () => {
        setIsSyncing(true);
        try {
            const res = await fetch(`${API_CONFIG.BASE_URL}/api/sync/tally`, {
                method: "POST",
                headers: API_CONFIG.getHeaders()
            });
            if (res.ok) {
                setShowSuccess(true);
                setTimeout(() => {
                    setShowSuccess(false);
                    window.location.reload();
                }, 2000);
            } else {
                const error = await res.json();
                alert(`Sync Failed: ${error.detail || 'Unknown error'}`);
            }
        } catch (error) {
            console.error("Sync error:", error);
            alert("Sync Error: Is backend running?");
        } finally {
            setIsSyncing(false);
        }
    };

    const handleSearch = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && searchQuery.trim()) {
            router.push(`/search?q=${encodeURIComponent(searchQuery)}`);
        }
    };

    return (
        <>
            {showSuccess && (
                <div className="fixed top-4 right-4 z-50 bg-emerald-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2 animate-in slide-in-from-top text-sm font-medium">
                    <CheckCircle2 className="h-4 w-4" />
                    <span>Sync Completed</span>
                </div>
            )}

            <header className="h-16 border-b px-6 flex items-center justify-between sticky top-0 z-30 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">

                {/* LEFT: Page Context */}
                <div className="flex flex-col justify-center">
                    <h1 className="text-lg font-bold text-foreground leading-none tracking-tight">
                        {currentPathConfig.title}
                    </h1>
                    {currentPathConfig.subtitle && (
                        <p className="text-[11px] text-muted-foreground mt-1 font-medium tracking-wide uppercase">
                            {currentPathConfig.subtitle}
                        </p>
                    )}
                </div>

                {/* RIGHT: Global Actions */}
                <div className="flex items-center gap-4">
                    {/* Search */}
                    <div className="relative w-64 hidden md:block group">
                        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground z-10" />
                        <Input
                            placeholder="Type to search..."
                            className="pl-9 h-9 bg-muted/30 border-none shadow-none focus-visible:ring-1 focus-visible:bg-background transition-all rounded-full text-sm relative z-10"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            onKeyDown={handleSearch}
                            onFocus={() => searchQuery.length > 1 && setIsOpen(true)}
                            onBlur={() => setTimeout(() => setIsOpen(false), 200)} // Delay to allow click
                        />

                        {/* Search Dropdown */}
                        {isOpen && results && (
                            <div className="absolute top-10 left-0 w-[400px] -ml-[72px] md:ml-0 md:w-full bg-white border rounded-lg shadow-xl overflow-hidden z-50 animate-in fade-in zoom-in-95">
                                <div className="max-h-[80vh] overflow-y-auto p-2 space-y-4">

                                    {/* Ledgers */}
                                    {results.ledgers?.length > 0 && (
                                        <div>
                                            <h4 className="text-xs font-semibold text-muted-foreground uppercase px-2 mb-1">Parties</h4>
                                            {results.ledgers.map((l: any) => (
                                                <div
                                                    key={l.id}
                                                    onClick={() => router.push(`/parties/${l.id}`)}
                                                    className="flex items-center justify-between p-2 rounded hover:bg-muted cursor-pointer text-sm"
                                                >
                                                    <span className="font-medium text-foreground">{l.name}</span>
                                                    <span className={`text-xs ${l.balance < 0 ? 'text-red-500' : 'text-green-500'}`}>
                                                        ₹{Math.abs(l.balance).toLocaleString()}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    {/* Items */}
                                    {results.items?.length > 0 && (
                                        <div>
                                            <h4 className="text-xs font-semibold text-muted-foreground uppercase px-2 mb-1">Inventory</h4>
                                            {results.items.map((i: any) => (
                                                <div
                                                    key={i.id}
                                                    // Assuming we have an item details page or just show specific info
                                                    className="flex items-center justify-between p-2 rounded hover:bg-muted cursor-pointer text-sm"
                                                >
                                                    <span className="font-medium text-foreground">{i.name}</span>
                                                    <div className="text-right">
                                                        <span className="text-xs text-muted-foreground block">{i.stock} {i.units}</span>
                                                        <span className="text-xs font-semibold">₹{i.rate}</span>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    {/* Vouchers */}
                                    {results.vouchers?.length > 0 && (
                                        <div>
                                            <h4 className="text-xs font-semibold text-muted-foreground uppercase px-2 mb-1">Transactions</h4>
                                            {results.vouchers.map((v: any) => (
                                                <div
                                                    key={v.id}
                                                    className="group flex flex-col p-2 rounded hover:bg-muted cursor-pointer text-sm"
                                                >
                                                    <div className="flex justify-between">
                                                        <span className="font-mono text-xs">{v.number}</span>
                                                        <span className="font-semibold">₹{v.amount.toLocaleString()}</span>
                                                    </div>
                                                    <div className="flex justify-between mt-1">
                                                        <span className="text-xs text-muted-foreground truncate max-w-[150px]">{v.party}</span>
                                                        <span className="text-[10px] uppercase bg-slate-100 px-1 rounded">{v.type}</span>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    {/* Empty State */}
                                    {!results.ledgers?.length && !results.items?.length && !results.vouchers?.length && (
                                        <div className="p-4 text-center text-sm text-muted-foreground">
                                            No results found.
                                        </div>
                                    )}
                                </div>
                                <div className="bg-muted/50 p-2 text-center text-xs text-muted-foreground border-t">
                                    Press Enter for advanced search
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="h-8 w-px bg-border mx-1 hidden md:block"></div>

                    {/* Sync Status Badge */}
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted/30 border border-border/50">
                        <div
                            className={cn("h-2 w-2 rounded-full animate-pulse", syncHealth.connected ? "bg-emerald-500" : "bg-red-500")}
                            title={syncHealth.connected ? "Online" : "Offline"}
                        />
                        <span className={cn("text-xs font-semibold", syncHealth.connected ? "text-emerald-700" : "text-red-700")}>
                            {syncHealth.connected ? "Live" : "Offline"}
                        </span>
                    </div>

                    <Button
                        size="sm"
                        variant="secondary"
                        onClick={handleSync}
                        disabled={isSyncing}
                        className={cn("h-8 gap-2 text-xs font-semibold rounded-full transition-all", isSyncing && "opacity-80")}
                    >
                        <RefreshCw className={cn("h-3.5 w-3.5", isSyncing && "animate-spin")} />
                        {isSyncing ? "Syncing..." : "Sync Now"}
                    </Button>

                    <Button size="icon" variant="ghost" className="h-8 w-8 rounded-full text-muted-foreground">
                        <Bell className="h-4 w-4" />
                    </Button>
                </div>
            </header>
        </>
    );
}
