"use client";

import { useState } from "react";
import { X, ArrowLeft, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { type Plan } from "@/lib/plans-config";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "https://weare-production.up.railway.app";

type Step = "form" | "paying" | "done";

interface FormData {
    name: string;
    company_name: string;
    email: string;
    phone: string;
    gst_number: string;
}

interface Props {
    plan: Plan;
    onClose: () => void;
}

// ─── Step 1: Contact Details Form ────────────────────────────────────────────

function DetailsForm({
    plan,
    onSubmit,
    loading,
    error,
}: {
    plan: Plan;
    onSubmit: (data: FormData) => void;
    loading: boolean;
    error: string | null;
}) {
    const [form, setForm] = useState<FormData>({
        name: "", company_name: "", email: "", phone: "", gst_number: "",
    });
    const set = (k: keyof FormData) =>
        (e: React.ChangeEvent<HTMLInputElement>) =>
            setForm(prev => ({ ...prev, [k]: e.target.value }));

    const fields: {
        key: keyof FormData;
        label: string;
        placeholder: string;
        type?: string;
        required?: boolean;
    }[] = [
            { key: "name", label: "Full name", placeholder: "Rajesh Kumar", required: true },
            { key: "company_name", label: "Company / firm name", placeholder: "Rajesh Traders Pvt.", required: true },
            { key: "email", label: "Email address", placeholder: "rajesh@company.com", type: "email", required: true },
            { key: "phone", label: "WhatsApp number", placeholder: "9876543210", type: "tel", required: true },
            { key: "gst_number", label: "GSTIN (optional)", placeholder: "27AAAAA0000A1Z5" },
        ];

    return (
        <form onSubmit={e => { e.preventDefault(); onSubmit(form); }} className="space-y-4">
            {/* Plan summary */}
            <div className="flex items-center justify-between p-4 rounded-xl bg-blue-50 border border-blue-100">
                <div>
                    <p className="text-xs text-blue-600 font-semibold uppercase tracking-wide">Selected plan</p>
                    <p className="text-slate-900 font-bold">{plan.name}</p>
                </div>
                <div className="text-right">
                    <p className="text-slate-900 font-bold">{plan.price_annual_display} / year</p>
                    <p className="text-slate-400 text-xs">+ 18% GST · billed annually</p>
                </div>
            </div>

            {/* Fields */}
            {fields.map(f => (
                <div key={f.key}>
                    <label className="block text-xs font-semibold text-slate-600 mb-1.5">
                        {f.label}{f.required && <span className="text-red-500 ml-0.5">*</span>}
                    </label>
                    <input
                        type={f.type || "text"}
                        value={form[f.key]}
                        onChange={set(f.key)}
                        placeholder={f.placeholder}
                        required={f.required}
                        className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-200 transition-all bg-white"
                    />
                </div>
            ))}

            {/* Error */}
            {error && (
                <div className="flex items-start gap-2.5 p-3 rounded-xl bg-red-50 border border-red-100 text-red-600 text-xs">
                    <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                    <span>{error}</span>
                </div>
            )}

            <button
                type="submit"
                disabled={loading}
                className="w-full py-3 rounded-xl bg-blue-700 text-white font-semibold text-sm hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
                {loading
                    ? <><Loader2 className="h-4 w-4 animate-spin" />Processing…</>
                    : "Continue to payment →"
                }
            </button>

            <p className="text-[11px] text-slate-400 text-center">
                You will be redirected to a secure Razorpay payment page.
            </p>
        </form>
    );
}

// ─── Step 2: Paying (loading / redirect) ─────────────────────────────────────

function PayingStep() {
    return (
        <div className="flex flex-col items-center justify-center py-12 space-y-4 text-center">
            <Loader2 className="h-10 w-10 animate-spin text-blue-600" />
            <p className="text-slate-800 font-semibold text-base">Opening secure payment page…</p>
            <p className="text-slate-400 text-sm max-w-xs">
                You will be redirected to Razorpay. Do not close this window.
            </p>
        </div>
    );
}

// ─── Step 3: Success ──────────────────────────────────────────────────────────

function DoneStep({ plan, onClose }: { plan: Plan; onClose: () => void }) {
    return (
        <div className="text-center py-4 space-y-6">
            <div className="flex justify-center">
                <div className="h-16 w-16 rounded-full bg-green-50 border border-green-100 flex items-center justify-center">
                    <CheckCircle className="h-8 w-8 text-green-600" />
                </div>
            </div>
            <div>
                <h3 className="text-xl font-bold text-slate-900 mb-2">Payment initiated</h3>
                <p className="text-slate-500 text-sm leading-relaxed max-w-sm mx-auto">
                    Complete your payment on the Razorpay page that opened. Your{" "}
                    <span className="font-semibold text-slate-900">{plan.name} plan</span>{" "}
                    account activates automatically within seconds of payment — no manual verification needed.
                </p>
            </div>

            <div className="flex gap-3">
                <a
                    href="https://wa.me/917851074499"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 py-3 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-50 text-sm font-medium transition-colors text-center"
                >
                    Contact support
                </a>
                <button
                    onClick={onClose}
                    className="flex-1 py-3 rounded-xl bg-blue-700 text-white text-sm font-semibold hover:bg-blue-800 transition-colors"
                >
                    Done
                </button>
            </div>
        </div>
    );
}

// ─── Main Modal ───────────────────────────────────────────────────────────────

export default function SubscribeModal({ plan, onClose }: Props) {
    const [step, setStep] = useState<Step>("form");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const STEP_LABELS: Record<Step, string> = {
        form: "Your details",
        paying: "Payment",
        done: "Confirmed",
    };

    const handleFormSubmit = async (data: FormData) => {
        setLoading(true);
        setError(null);
        try {
            // Read existing tenant_id from localStorage
            let existingTenantId: string | null = null;
            try {
                const userData = localStorage.getItem("k24_user");
                if (userData) {
                    const parsed = JSON.parse(userData);
                    existingTenantId = parsed.tenant_id || null;
                }
            } catch (e) {
                // Ignore localStorage errors
            }

            const headers: Record<string, string> = { "Content-Type": "application/json" };
            const token = localStorage.getItem("k24_token");
            if (token) {
                headers["Authorization"] = `Bearer ${token}`;
            }

            const res = await fetch(`${BACKEND_URL}/api/payments/create-link`, {
                method: "POST",
                headers,
                body: JSON.stringify({
                    tenant_id: existingTenantId,
                    plan_id: plan.id,
                    customer_name: data.name,
                    customer_email: data.email,
                    customer_phone: data.phone,
                    source: "pricing_page",
                }),
            });
            const json = await res.json();
            if (!res.ok) throw new Error(json.detail || "Something went wrong. Please try again.");

            const paymentLinkUrl: string = json.payment_link_url;

            // Show loading state briefly before redirect
            setStep("paying");
            setLoading(false);

            setTimeout(() => {
                window.open(paymentLinkUrl, "_blank");
                setStep("done");
            }, 800);
        } catch (e: any) {
            setError(e.message);
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/40"
                onClick={step !== "done" ? onClose : undefined}
            />

            {/* Modal */}
            <div className="relative z-10 w-full max-w-md bg-white border border-slate-200 rounded-2xl shadow-xl overflow-hidden">

                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
                    <div>
                        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide">
                            {step === "form" ? "Step 1 of 2" : step === "paying" ? "Step 2 of 2" : "Complete"}
                        </p>
                        <h2 className="text-sm font-bold text-slate-900">{STEP_LABELS[step]}</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors"
                    >
                        <X className="h-4 w-4" />
                    </button>
                </div>

                {/* Progress bar */}
                <div className="flex gap-1.5 px-6 py-2.5 border-b border-slate-100 bg-slate-50">
                    {(["form", "paying", "done"] as Step[]).map((s, i) => (
                        <div
                            key={s}
                            className={`flex-1 h-1 rounded-full transition-all ${(step === "form" && i === 0) ||
                                    (step === "paying" && i <= 1) ||
                                    step === "done"
                                    ? "bg-blue-600"
                                    : "bg-slate-200"
                                }`}
                        />
                    ))}
                </div>

                {/* Content */}
                <div className="p-6 max-h-[75vh] overflow-y-auto">
                    {step === "form" && (
                        <DetailsForm
                            plan={plan}
                            onSubmit={handleFormSubmit}
                            loading={loading}
                            error={error}
                        />
                    )}
                    {step === "paying" && <PayingStep />}
                    {step === "done" && (
                        <DoneStep plan={plan} onClose={onClose} />
                    )}
                </div>
            </div>
        </div>
    );
}
