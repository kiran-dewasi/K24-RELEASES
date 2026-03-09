/**
 * Admin Portal — Typed API client
 * All admin data access goes through these typed fetch wrappers.
 * Uses the internal K24 backend API directly.
 */

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8001";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "k24-secret-key-123";

const headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY,
};

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
    const res = await fetch(`${BACKEND_URL}${path}`, {
        ...options,
        headers: { ...headers, ...(options?.headers || {}) },
    });
    if (!res.ok) {
        const txt = await res.text();
        throw new Error(`API ${path} → ${res.status}: ${txt.slice(0, 200)}`);
    }
    return res.json() as Promise<T>;
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface TenantRow {
    tenant_id: string;
    company_name: string;
    plan_id: string;
    plan_name: string;
    plan_status: string;
    enforcement_mode: string;
    companies_count: number;
    credits_used: number;
    max_credits: number;
    percent_used: number;
    next_cycle_end: string | null;
    created_at: string | null;
}

export interface TenantListResponse {
    tenants: TenantRow[];
    total: number;
}

export interface LLMSummary {
    total_calls: number;
    total_tokens_in: number;
    total_tokens_out: number;
    total_tokens: number;
    total_cost_usd: number;
    top_workflows: { workflow: string; calls: number; tokens: number; cost_usd: number }[];
}

export interface TenantDetail {
    tenant: {
        id: string;
        company_name: string;
        whatsapp_number: string | null;
        created_at: string | null;
    };
    plan: {
        plan_id: string;
        plan_name: string;
        status: string;
        enforcement_mode: string;
        max_credits: number;
        max_companies: number;
        features: Record<string, boolean>;
        current_period_end: string | null;
    };
    current_cycle: {
        id: string | null;
        cycle_start: string | null;
        cycle_end: string | null;
        max_credits: number;
        credits_used_total: number;
        credits_used_voucher: number;
        credits_used_document: number;
        credits_used_message: number;
        events_count_total: number;
        events_count_voucher: number;
        events_count_document: number;
        events_count_message: number;
        percent_used: number;
    };
    recent_events: UsageEvent[];
    llm_summary: LLMSummary;
}

export interface UsageEvent {
    id: string;
    event_type: string;
    event_subtype: string;
    credits_consumed: number;
    source: string;
    status: string;
    metadata_json: Record<string, unknown>;
    created_at: string;
}

export interface Plan {
    id: string;
    display_name: string;
    price_monthly_paise: number;
    max_credits_per_cycle: number;
    max_companies: number;
    enforcement_mode: string;
    features_json: Record<string, boolean>;
    is_active: boolean;
}

export interface CreditRule {
    id: string;
    event_type: string;
    event_subtype: string;
    credits: number;
    description: string | null;
    effective_from: string;
    effective_to: string | null;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

// ─── API Functions ────────────────────────────────────────────────────────────

export async function fetchTenants(params?: {
    search?: string;
    plan_id?: string;
}): Promise<TenantListResponse> {
    const qs = new URLSearchParams();
    if (params?.search) qs.set("search", params.search);
    if (params?.plan_id) qs.set("plan_id", params.plan_id);
    const qstr = qs.toString();
    return apiFetch<TenantListResponse>(`/admin/tenants${qstr ? `?${qstr}` : ""}`);
}

export async function fetchTenantDetail(tenantId: string, eventsLimit = 20): Promise<TenantDetail> {
    return apiFetch<TenantDetail>(`/admin/tenants/${tenantId}/usage?events_limit=${eventsLimit}`);
}

export async function fetchPlans(): Promise<{ plans: Plan[] }> {
    return apiFetch<{ plans: Plan[] }>("/admin/plans");
}

export async function fetchCreditRules(): Promise<{ credit_rules: CreditRule[]; total: number }> {
    return apiFetch<{ credit_rules: CreditRule[]; total: number }>("/admin/credit-rules");
}

export async function updateCreditRule(
    ruleId: string,
    data: { credits?: number; description?: string; is_active?: boolean; effective_to?: string }
): Promise<{ credit_rule: CreditRule; cache_invalidated: boolean }> {
    return apiFetch(`/admin/credit-rules/${ruleId}`, {
        method: "PUT",
        body: JSON.stringify(data),
    });
}

export async function createCreditRule(data: {
    event_type: string;
    event_subtype: string;
    credits: number;
    description?: string;
}): Promise<{ credit_rule: CreditRule; cache_invalidated: boolean }> {
    return apiFetch(`/admin/credit-rules`, {
        method: "POST",
        body: JSON.stringify(data),
    });
}

export async function assignPlan(
    tenantId: string,
    data: { plan_id: string; status?: string; notes?: string }
): Promise<{ success: boolean; tenant_id: string; plan_id: string }> {
    return apiFetch(`/admin/tenants/${tenantId}/assign-plan`, {
        method: "POST",
        body: JSON.stringify(data),
    });
}

// Helpers
export const fmtPaise = (paise: number): string =>
    paise === 0 ? "Custom" : `₹${(paise / 100).toLocaleString("en-IN")}/mo`;

export const fmtDate = (iso: string | null | undefined): string => {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("en-IN", {
        day: "2-digit", month: "short", year: "numeric",
    });
};

export const statusColor = (status: string): string => {
    switch (status) {
        case "active": return "text-emerald-400";
        case "trial": return "text-amber-400";
        case "suspended": return "text-red-400";
        default: return "text-slate-400";
    }
};

export const creditStatusColor = (pct: number): string => {
    if (pct >= 100) return "#ef4444";
    if (pct >= 80) return "#f59e0b";
    return "#10b981";
};
