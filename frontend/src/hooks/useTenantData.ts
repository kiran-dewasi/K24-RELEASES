"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { API_CONFIG } from "@/lib/api-config";

interface TenantDataState<T> {
    data: T | null;
    loading: boolean;
    error: string | null;
}

export function useTenantData<T>(endpoint: string, initialData: T | null = null) {
    const router = useRouter();
    const [state, setState] = useState<TenantDataState<T>>({
        data: initialData,
        loading: true,
        error: null,
    });

    useEffect(() => {
        let isMounted = true;

        const fetchData = async () => {
            try {
                const res = await fetch(`${API_CONFIG.BASE_URL}${endpoint}`, {
                    headers: API_CONFIG.getHeaders(),
                });

                if (res.status === 401) {
                    router.push("/login");
                    return;
                }

                if (!res.ok) {
                    throw new Error(`API Error: ${res.statusText}`);
                }

                const jsonData = await res.json();

                if (isMounted) {
                    setState({ data: jsonData, loading: false, error: null });
                }
            } catch (err: any) {
                if (isMounted) {
                    setState({ data: null, loading: false, error: err.message || "Failed to fetch data" });
                }
            }
        };

        fetchData();

        return () => {
            isMounted = false;
        };
    }, [endpoint, router]);

    return state;
}
