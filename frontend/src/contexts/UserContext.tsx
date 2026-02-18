"use client";

import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";
import { apiRequest } from "@/lib/api";

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

            const data = await apiRequest<User>("/api/auth/me");
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
