/**
 * K24 Secure API Client
 * 
 * All API calls go through the Tauri backend_request command for security.
 * In development, falls back to direct HTTP if Tauri is not available.
 * 
 * Security Features:
 * - Session token validation (X-Desktop-Token header)
 * - Dynamic port allocation in production
 * - All requests proxied through Rust layer
 */

// Check if running in Tauri
const isTauri = () => {
    return typeof window !== 'undefined' && (
        '__TAURI_INTERNALS__' in window || '__TAURI__' in window
    );
};

// In Tauri DEV mode (npx tauri dev), Next.js runs on localhost so backend is
// the external uvicorn on port 8001 — use direct HTTP, not Rust invoke().
// In PRODUCTION Tauri build, use Rust invoke('backend_request') for security.
// IMPORTANT: Check process.env.NODE_ENV only (not window.location) to avoid false positives
const isTauriDev = () => {
    // In production build, NODE_ENV is 'production' at build time
    // Only return true if we're actually in development mode
    return isTauri() && process.env.NODE_ENV === 'development';
};

// Development fallback configuration
const DEV_API_URL = process.env.NEXT_PUBLIC_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001';

// API key for local backend routes that use Depends(get_api_key)
// This matches API_KEY in backend/dependencies.py (env: API_KEY, default: 'k24-secret-key-123')
const LOCAL_API_KEY = process.env.NEXT_PUBLIC_API_KEY || 'k24-secret-key-123';

/**
 * Get JWT token from localStorage
 */
const getAuthToken = (): string | null => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('k24_token');
};

/**
 * Make a secure API request
 * 
 * In Tauri: Uses Rust backend_request command with session token
 * In Browser: Falls back to direct HTTP with JWT token
 * 
 * @param endpoint - API endpoint (e.g., '/api/dashboard/stats')
 * @param method - HTTP method (GET, POST, PUT, DELETE)
 * @param body - Optional request body
 * @returns Promise with parsed JSON response
 */
export async function apiRequest<T = any>(
    endpoint: string,
    method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET',
    body?: any
): Promise<T> {
    const authToken = getAuthToken();

    // In Tauri production build: use Rust backend_request command for security
    // In Tauri dev mode: fall through to direct HTTP (same as browser dev)
    if (isTauri() && !isTauriDev()) {
        try {
            const { invoke } = await import('@tauri-apps/api/core');

            const response = await invoke<string>('backend_request', {
                endpoint,
                method,
                body: body ? JSON.stringify(body) : null,
                authToken
            });

            try {
                return JSON.parse(response);
            } catch {
                return response as unknown as T;
            }
        } catch (error: any) {
            console.error('Tauri API request failed:', error);

            // Handle authentication errors
            if (error.includes?.('401') || error.includes?.('Unauthorized')) {
                handleAuthError();
            }

            throw new Error(error?.message || error);
        }
    } else {
        // Dev mode: route through Next.js proxy to avoid Tauri WebView fetch restrictions.
        // In plain browser (no Tauri), fetch directly to the backend.
        // Development / Tauri dev: Direct HTTP to backend
        const url = endpoint.startsWith('http') ? endpoint : `${DEV_API_URL}${endpoint}`;

        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
            'x-api-key': LOCAL_API_KEY,  // Required by dashboard & other routes using Depends(get_api_key)
        };

        if (authToken) {
            headers['Authorization'] = `Bearer ${authToken}`;
        }

        const options: RequestInit = {
            method,
            headers,
        };

        if (body && method !== 'GET') {
            options.body = JSON.stringify(body);
        }

        const response = await fetch(url, options);

        if (response.status === 401) {
            handleAuthError();
            throw new Error('Unauthorized');
        }

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || `HTTP ${response.status}`);
        }

        const contentType = response.headers.get('content-type');
        if (contentType?.includes('application/json')) {
            return response.json();
        }

        return response.text() as unknown as T;
    }
}

/**
 * Handle authentication errors (logout and redirect)
 */
function handleAuthError() {
    if (typeof window !== 'undefined') {
        // Import toast dynamically to show notification
        import('@/components/ui/use-toast').then(({ toast }) => {
            toast({
                title: "Session expired",
                description: "Please login again.",
                variant: "destructive",
            });
        });

        localStorage.removeItem('k24_token');
        localStorage.removeItem('k24_user');

        // Delay redirect slightly to allow toast to be visible
        setTimeout(() => {
            window.location.href = '/login';
        }, 1500);
    }
}

/**
 * Check if backend is running
 */
export async function checkBackendStatus(): Promise<{ running: boolean; port?: number }> {
    // In Tauri production build, ask Rust for backend status
    if (isTauri() && !isTauriDev()) {
        try {
            const { invoke } = await import('@tauri-apps/api/core');
            return await invoke('get_backend_status');
        } catch {
            return { running: false };
        }
    }

    // Dev mode (browser or Tauri dev): check external uvicorn directly
    try {
        const response = await fetch(`${DEV_API_URL}/health`, {
            method: 'GET',
            signal: AbortSignal.timeout(5000)
        });
        return { running: response.ok, port: 8001 };
    } catch {
        return { running: false };
    }
}

/**
 * Start the backend (Tauri only)
 */
export async function startBackend(): Promise<{ port: number; mode: string }> {
    if (!isTauri() || isTauriDev()) {
        // Development mode - backend is external uvicorn
        return { port: 8001, mode: 'development' };
    }

    const { invoke } = await import('@tauri-apps/api/core');
    return await invoke('start_backend');
}

// ============================================================
// Convenience methods for common API operations
// ============================================================

export const api = {
    get: <T = any>(endpoint: string) => apiRequest<T>(endpoint, 'GET'),
    post: <T = any>(endpoint: string, body?: any) => apiRequest<T>(endpoint, 'POST', body),
    put: <T = any>(endpoint: string, body?: any) => apiRequest<T>(endpoint, 'PUT', body),
    delete: <T = any>(endpoint: string) => apiRequest<T>(endpoint, 'DELETE'),
};

// ============================================================
// Legacy compatibility - these mirror the old API_CONFIG
// ============================================================

export const API_CONFIG = {
    BASE_URL: DEV_API_URL,

    getHeaders: () => {
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
            'x-api-key': LOCAL_API_KEY,  // Required by routes using Depends(get_api_key)
        };

        if (typeof window !== 'undefined') {
            const token = localStorage.getItem('k24_token');
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
        }

        return headers;
    }
};

/**
 * Legacy apiClient function for backward compatibility
 * @deprecated Use apiRequest instead
 */
export async function apiClient(endpoint: string, options: RequestInit = {}): Promise<Response> {
    const url = endpoint.startsWith('http') ? endpoint : `${DEV_API_URL}${endpoint}`;

    const headers: Record<string, string> = {
        ...API_CONFIG.getHeaders(),
        ...(options.headers as Record<string, string> || {})
    };

    const res = await fetch(url, {
        ...options,
        headers
    });

    if (res.status === 401) {
        handleAuthError();
    }

    return res;
}
