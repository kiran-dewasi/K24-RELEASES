"use client";

import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";
import { apiRequest } from "@/lib/api";

const CLOUD_API = "https://weare-production.up.railway.app";

// ============================================================
// Types
// ============================================================

export interface User {
    id: number;
    email: string;
    username: string;
    full_name: string;
    role: string;
    company_id: number | null;
    tenant_id: string | null;
    whatsapp_number: string | null;
    is_whatsapp_verified: boolean;
    subscription_status: string | null;
    trial_ends_at: string | null;
}

interface UserContextValue {
    user: User | null;
    loading: boolean;
    error: string | null;
    refreshUser: () => Promise<void>;
}

// ============================================================
// Context
// ============================================================

const UserContext = createContext<UserContextValue>({
    user: null,
    loading: true,
    error: null,
    refreshUser: async () => { },
});

// ============================================================
// Provider
// ============================================================

function handleCloudAuthError() {
    if (typeof window !== "undefined") {
        localStorage.removeItem("k24_token");
        localStorage.removeItem("k24_user");
        window.location.href = "/login";
    }
}

export function UserProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchUser = useCallback(async () => {
        // No token → user is not logged in. Finish loading immediately.
        if (typeof window !== "undefined" && !localStorage.getItem("k24_token")) {
            setUser(null);
            setLoading(false);
            return;
        }

        try {
            setLoading(true);
            setError(null);

            const token = typeof window !== "undefined" ? localStorage.getItem("k24_token") : null;
            const res = await fetch(`${CLOUD_API}/api/auth/me`, {
                headers: {
                    "Content-Type": "application/json",
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
            });
            if (res.status === 401) {
                handleCloudAuthError();
                throw new Error("Unauthorized");
            }
            if (!res.ok) {
                const text = await res.text();
                throw new Error(text || `HTTP ${res.status}`);
            }
            const data: User = await res.json();
            setUser(data);

            // Cache user data for offline fallback
            if (typeof window !== "undefined") {
                localStorage.setItem("k24_user", JSON.stringify(data));
            }
        } catch (err: any) {
            const message = err?.message || "Failed to load user";

            // 401 is already handled by apiRequest (clears token + redirects to /login)
            if (!message.includes("Unauthorized")) {
                // Try cached user for offline mode
                if (typeof window !== "undefined") {
                    const cached = localStorage.getItem("k24_user");
                    if (cached) {
                        try {
                            setUser(JSON.parse(cached));
                            setError("Offline – using cached data");
                            setLoading(false);
                            return;
                        } catch {
                            // corrupted cache, ignore
                        }
                    }
                }
                setError(message);
            }

            setUser(null);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchUser();
    }, [fetchUser]);

    return (
        <UserContext.Provider value={{ user, loading, error, refreshUser: fetchUser }}>
            {children}
        </UserContext.Provider>
    );
}

// ============================================================
// Hook
// ============================================================

export function useUser() {
    return useContext(UserContext);
}
