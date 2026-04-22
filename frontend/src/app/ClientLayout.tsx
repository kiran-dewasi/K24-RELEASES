"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import Navbar from "@/components/Navbar";
import { Toaster } from "@/components/ui/toaster";
import { UserProvider } from "@/contexts/UserContext";
import { SidebarProvider, useSidebar } from "@/contexts/SidebarContext";
import { ChatProvider } from "@/contexts/ChatContext";
import AuthGuard from "@/components/AuthGuard";
import TrialBanner from "@/components/TrialBanner";
import { setBackendPort } from "@/lib/api";

// ── Tauri detection ──────────────────────────────────────────────────────────
const isTauri = () =>
    typeof window !== "undefined" &&
    ("__TAURI_INTERNALS__" in window || "__TAURI__" in window);

// ── StartupScreen ────────────────────────────────────────────────────────────
function StartupScreen() {
    return (
        <div
            style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                height: "100vh",
                background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
                color: "#f8fafc",
                fontFamily: "'Inter', system-ui, sans-serif",
            }}
        >
            {/* Logo / wordmark */}
            <div
                style={{
                    fontSize: "2.5rem",
                    fontWeight: 800,
                    letterSpacing: "-0.04em",
                    background: "linear-gradient(90deg, #38bdf8, #818cf8)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                    marginBottom: "1.5rem",
                }}
            >
                K24
            </div>

            {/* Spinner */}
            <style>{`
                @keyframes k24-spin {
                    to { transform: rotate(360deg); }
                }
                .k24-spinner {
                    width: 40px;
                    height: 40px;
                    border: 3px solid rgba(56,189,248,0.25);
                    border-top-color: #38bdf8;
                    border-radius: 50%;
                    animation: k24-spin 0.8s linear infinite;
                    margin-bottom: 1.25rem;
                }
            `}</style>
            <div className="k24-spinner" />

            <p style={{ color: "#94a3b8", fontSize: "0.875rem", letterSpacing: "0.05em" }}>
                Starting up…
            </p>
        </div>
    );
}

// ── CrashScreen ──────────────────────────────────────────────────────────────
function CrashScreen({ reason }: { reason: string }) {
    const handleRestart = async () => {
        if (isTauri()) {
            try {
                const { relaunch } = await import("@tauri-apps/plugin-process");
                await relaunch();
            } catch {
                window.location.reload();
            }
        } else {
            window.location.reload();
        }
    };

    return (
        <div
            style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                height: "100vh",
                background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
                color: "#f8fafc",
                fontFamily: "'Inter', system-ui, sans-serif",
                textAlign: "center",
                padding: "2rem",
            }}
        >
            {/* Warning icon */}
            <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>⚠️</div>

            <h1
                style={{
                    fontSize: "1.5rem",
                    fontWeight: 700,
                    color: "#f87171",
                    marginBottom: "0.75rem",
                }}
            >
                Backend failed to start
            </h1>

            <p
                style={{
                    color: "#94a3b8",
                    fontSize: "0.875rem",
                    background: "rgba(0,0,0,0.3)",
                    padding: "0.75rem 1.25rem",
                    borderRadius: "0.5rem",
                    maxWidth: "480px",
                    marginBottom: "2rem",
                    wordBreak: "break-word",
                }}
            >
                {reason || "Unknown error"}
            </p>

            <button
                onClick={handleRestart}
                style={{
                    background: "linear-gradient(90deg, #38bdf8, #818cf8)",
                    color: "#0f172a",
                    border: "none",
                    borderRadius: "0.5rem",
                    padding: "0.625rem 1.5rem",
                    fontSize: "0.875rem",
                    fontWeight: 700,
                    cursor: "pointer",
                    letterSpacing: "0.02em",
                }}
            >
                Restart App
            </button>
        </div>
    );
}

// ── InnerLayout (unchanged) ──────────────────────────────────────────────────
function InnerLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const { collapsed } = useSidebar();

    // Chat page: full-height workbench — no navbar, no padding, no max-width
    const isFullWorkbench = pathname.startsWith("/chat");

    return (
        <div className="flex bg-[#F8F9FC] min-h-screen">
            <Sidebar />
            <div
                className="flex flex-col h-screen overflow-hidden transition-[margin-left] duration-300 ease-in-out flex-1"
                style={{ marginLeft: collapsed ? "60px" : "260px" }}
            >
                {/* Navbar is hidden for the full-workbench chat page */}
                {!isFullWorkbench && <Navbar />}

                {/* Trial banner — between Navbar and page content, hidden on chat workbench */}
                {!isFullWorkbench && <TrialBanner />}

                {isFullWorkbench ? (
                    // Full workbench — takes full height, no navbar overhead
                    <div className="flex-1 overflow-hidden">
                        {children}
                    </div>
                ) : (
                    <main className="flex-1 p-8 overflow-y-auto">
                        <div className="max-w-7xl mx-auto">
                            {children}
                        </div>
                    </main>
                )}
            </div>
            <Toaster />
        </div>
    );
}

// ── Public-page list ─────────────────────────────────────────────────────────
const PUBLIC_PREFIXES = [
    "/login",
    "/signup",
    "/onboarding",
    "/forgot-password",
    "/reset-password",
    "/auth",
    "/pricing",
    "/subscribe",
    "/admin",
];

// ── ClientLayout (startup guard) ─────────────────────────────────────────────
export default function ClientLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();

    const [appState, setAppState] = useState<"starting" | "ready" | "crashed">("starting");
    const [crashReason, setCrashReason] = useState<string>("");

    // ── Public pages bypass the guard entirely ────────────────────────────────
    const isPublicPage = PUBLIC_PREFIXES.some((p) => pathname.startsWith(p));
    if (isPublicPage) return <>{children}<Toaster /></>;

    // ── Startup guard effect ──────────────────────────────────────────────────
    // eslint-disable-next-line react-hooks/rules-of-hooks
    useEffect(() => {
        // If not running in Tauri (plain browser), skip event dance and go ready
        if (!isTauri()) {
            setAppState("ready");
            return;
        }

        let unlistenReady: (() => void) | undefined;
        let unlistenError: (() => void) | undefined;

        (async () => {
            try {
                const { listen } = await import("@tauri-apps/api/event");
                const { invoke } = await import("@tauri-apps/api/core");

                // 1. Register backend_ready listener FIRST
                unlistenReady = await listen<{ port: number }>("backend_ready", (event) => {
                    const port = event.payload?.port ?? 0;
                    if (port > 0) {
                        setBackendPort(port);
                        setAppState("ready");
                    } else {
                        setCrashReason("Backend ready but port invalid");
                        setAppState("crashed");
                    }
                });

                // 2. Register backend_error listener SECOND
                unlistenError = await listen<string>("backend_error", (event) => {
                    setCrashReason(event.payload || "Backend failed to start");
                    setAppState("crashed");
                });

                // 3. NOW check if already ready (handles fast-start or re-mount)
                const result = await invoke<{ status: string; port?: number; error?: string }>(
                    "get_backend_status"
                );

                if (result.status === "ready" && (result.port ?? 0) > 0) {
                    setBackendPort(result.port!);
                    setAppState("ready");
                } else if (result.status === "crashed") {
                    setCrashReason(result.error || "Unknown error");
                    setAppState("crashed");
                }
                // else: status is "starting" or "not_started" — wait for events
            } catch (err) {
                // Tauri invoke failed — treat as not-yet-ready, keep waiting
                console.warn("[K24] Startup guard: invoke failed, waiting for events", err);
            }
        })();

        return () => {
            unlistenReady?.();
            unlistenError?.();
        };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // ── Render startup screens ────────────────────────────────────────────────
    if (appState === "starting") return <StartupScreen />;
    if (appState === "crashed") return <CrashScreen reason={crashReason} />;

    // ── appState === "ready" — normal app ────────────────────────────────────
    return (
        <UserProvider>
            <SidebarProvider>
                <ChatProvider>
                    <AuthGuard>
                        <InnerLayout>{children}</InnerLayout>
                    </AuthGuard>
                </ChatProvider>
            </SidebarProvider>
        </UserProvider>
    );
}
