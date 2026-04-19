"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiRequest } from "@/lib/api";

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
                const jsonData = await apiRequest<T>(endpoint);

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
    }, [endpoint]);

    return state;
}
