"use client";

import { useState } from "react";
import { X, Copy, Check, ArrowLeft, Loader2, CheckCircle, Smartphone, AlertCircle } from "lucide-react";
import { type Plan, UPI_CONFIG } from "@/lib/plans-config";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8001";

type Step = "form" | "upi" | "done";

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

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatINR(paise: number) {
    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0,
    }).format(paise / 100);
}

function CopyButton({ text }: { text: string }) {
    const [copied, setCopied] = useState(false);
    const copy = async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };
    return (
        <button
            onClick={copy}
            className="p-1.5 rounded-md hover:bg-slate-100 transition-colors text-slate-400 hover:text-slate-700"
            title="Copy"
        >
            {copied
                ? <Check className="h-3.5 w-3.5 text-green-600" />
                : <Copy className="h-3.5 w-3.5" />
            }
        </button>
    );
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
                    ? <><Loader2 className="h-4 w-4 animate-spin" /> Processing…</>
                    : "Continue to payment →"
                }
            </button>

            <p className="text-[11px] text-slate-400 text-center">
                After submitting, you will receive UPI payment instructions.
            </p>
        </form>
    );
}

// ─── Step 2: UPI Payment Instructions ────────────────────────────────────────

function UpiStep({
    plan,
    intentId,
    onSubmit,
    onBack,
    loading,
    error,
}: {
    plan: Plan;
    intentId: string;
    onSubmit: (ref: string) => void;
    onBack: () => void;
    loading: boolean;
    error: string | null;
}) {
    const [upiRef, setUpiRef] = useState("");

    // Annual amount ex-GST
    const amountRupees   = plan.price_annual_rupees;
    // GST-inclusive total — this is what the user actually pays
    const gstAmount      = Math.round(amountRupees * plan.gst_rate);
    const totalWithGst   = amountRupees + gstAmount;

    const fmtINR = (n: number) =>
        new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);

    // UPI deep link — amount MUST be GST-inclusive (what hits your bank)
    const deepLink =
        `upi://pay?pa=${UPI_CONFIG.upi_id}` +
        `&pn=${encodeURIComponent(UPI_CONFIG.payee_name)}` +
        `&am=${totalWithGst}` +
        `&cu=INR` +
        `&tn=${encodeURIComponent(`K24 ${plan.name} Plan (incl. 18% GST)`)}`;

    // Live QR — encodes the GST-inclusive total
    const qrUrl =
        `https://api.qrserver.com/v1/create-qr-code/?size=180x180&margin=8&data=` +
        encodeURIComponent(deepLink);

    return (
        <div className="space-y-5">
            {/* Step header with price breakdown */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                <p className="text-xs text-slate-500 font-semibold uppercase tracking-wide">{plan.name} Plan · Annual</p>
                <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Plan price (ex-GST)</span>
                    <span className="text-slate-700 font-medium">{fmtINR(amountRupees)}</span>
                </div>
                <div className="flex justify-between text-sm">
                    <span className="text-slate-500">GST @ 18%</span>
                    <span className="text-slate-700 font-medium">+ {fmtINR(gstAmount)}</span>
                </div>
                <div className="flex justify-between text-sm border-t border-slate-200 pt-2 mt-1">
                    <span className="text-slate-900 font-bold">Total to pay</span>
                    <span className="text-blue-700 font-bold text-base">{fmtINR(totalWithGst)}</span>
                </div>
            </div>

            {/* UPI details */}
            <div className="border border-slate-200 rounded-2xl overflow-hidden">
                {/* QR Code */}
                <div className="flex flex-col items-center py-6 bg-white border-b border-slate-100">
                    <div className="w-48 h-48 bg-white border border-slate-200 rounded-xl flex items-center justify-center mb-3 overflow-hidden">
                        {/* Live QR generated from UPI deep link */}
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                            src={qrUrl}
                            alt={`Scan to pay ${amountDisplay} to ${UPI_CONFIG.upi_id}`}
                            width={180}
                            height={180}
                            className="w-full h-full object-contain"
                        />
                    </div>
                    <p className="text-xs text-slate-500 font-medium mb-2">Scan with any UPI app to pay</p>
                    <p className="text-[11px] text-slate-400 mb-3">PhonePe · GPay · Paytm · BHIM · any bank app</p>

                    <p className="text-xs text-slate-400 mb-1">Or pay to UPI ID</p>
                    <div className="flex items-center gap-2 px-4 py-2 border border-slate-200 rounded-xl bg-slate-50">
                        <span className="font-mono text-sm font-semibold text-slate-900">{UPI_CONFIG.upi_id}</span>
                        <CopyButton text={UPI_CONFIG.upi_id} />
                    </div>
                    <div className="flex items-center gap-2 mt-2 text-sm">
                        <span className="text-slate-500">Amount to transfer:</span>
                        <span className="font-bold text-slate-900">{fmtINR(totalWithGst)}</span>
                        <CopyButton text={String(totalWithGst)} />
                    </div>
                    <p className="text-[10px] text-slate-400 mt-1">Includes ₹{gstAmount.toLocaleString("en-IN")} GST (18%)</p>
                </div>

                {/* Open payment app */}
                <a
                    href={deepLink}
                    className="flex items-center justify-center gap-2 w-full py-3 bg-green-50 border-b border-slate-100 text-green-700 text-sm font-medium hover:bg-green-100 transition-colors"
                >
                    Open in PhonePe / GPay / Paytm
                </a>

                {/* UTR input */}
                <div className="p-4 bg-white">
                    <label className="block text-xs font-semibold text-slate-600 mb-1.5">
                        UTR / Transaction reference number <span className="text-red-500">*</span>
                    </label>
                    <input
                        type="text"
                        value={upiRef}
                        onChange={e => setUpiRef(e.target.value)}
                        placeholder="e.g. 412345678901"
                        className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-200 transition-all"
                    />
                    <p className="text-[11px] text-slate-400 mt-1">
                        12-digit number available in your bank SMS or payment app under transaction history.
                    </p>
                </div>
            </div>

            {/* Error */}
            {error && (
                <div className="flex items-start gap-2 p-3 rounded-xl bg-red-50 border border-red-100 text-red-600 text-xs">
                    <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                    {error}
                </div>
            )}

            {/* Actions */}
            <div className="flex gap-3">
                <button
                    onClick={onBack}
                    className="flex items-center gap-1.5 px-4 py-3 rounded-xl border border-slate-200 text-slate-500 hover:text-slate-700 hover:bg-slate-50 text-sm transition-colors"
                >
                    <ArrowLeft className="h-3.5 w-3.5" /> Back
                </button>
                <button
                    onClick={() => upiRef.trim().length >= 6 && onSubmit(upiRef.trim())}
                    disabled={loading || upiRef.trim().length < 6}
                    className="flex-1 py-3 rounded-xl bg-blue-700 text-white font-semibold text-sm hover:bg-blue-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                >
                    {loading
                        ? <><Loader2 className="h-4 w-4 animate-spin" /> Submitting…</>
                        : "Confirm payment ✓"
                    }
                </button>
            </div>
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
                <h3 className="text-xl font-bold text-slate-900 mb-2">Payment submitted</h3>
                <p className="text-slate-500 text-sm leading-relaxed max-w-sm mx-auto">
                    Your request for the <span className="font-semibold text-slate-900">{plan.name} plan</span> is received.
                    Our team will verify payment within <strong className="text-slate-900">{UPI_CONFIG.verification_hours} business hours</strong> and
                    send your access credentials to the email and WhatsApp number you provided.
                </p>
            </div>

            {/* Next steps */}
            <div className="text-left border border-slate-200 rounded-xl p-4 space-y-2.5 bg-slate-50">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">What happens next</p>
                {[
                    "We verify your UTR against our bank records",
                    "Login credentials sent to your email",
                    "Activation confirmation on WhatsApp",
                    "You connect Tally and start automating",
                ].map((step, i) => (
                    <div key={i} className="flex items-center gap-2.5 text-sm text-slate-600">
                        <span className="h-5 w-5 rounded-full bg-blue-100 text-blue-700 text-[10px] flex items-center justify-center font-bold shrink-0">
                            {i + 1}
                        </span>
                        {step}
                    </div>
                ))}
            </div>

            <div className="flex gap-3">
                <a
                    href={`https://wa.me/${UPI_CONFIG.support_whatsapp.replace(/\D/g, "")}`}
                    target="_blank"
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
    const [intentId, setIntentId] = useState<string>("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const STEP_LABELS: Record<Step, string> = {
        form: "Your details",
        upi: "Payment",
        done: "Confirmed",
    };

    const handleFormSubmit = async (data: FormData) => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${BACKEND_URL}/public/subscribe/intent`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ plan_id: plan.id, ...data }),
            });
            const json = await res.json();
            if (!res.ok) throw new Error(json.detail || "Something went wrong. Please try again.");
            setIntentId(json.intent_id);
            setStep("upi");
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    const handlePaymentSubmit = async (ref: string) => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(
                `${BACKEND_URL}/public/subscribe/intent/${intentId}/payment`,
                {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ upi_ref: ref }),
                }
            );
            const json = await res.json();
            if (!res.ok) throw new Error(json.detail || "Failed to submit payment. Please try again.");
            setStep("done");
        } catch (e: any) {
            setError(e.message);
        } finally {
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
                            {step === "form" ? "Step 1 of 2" : step === "upi" ? "Step 2 of 2" : "Complete"}
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
                    {(["form", "upi", "done"] as Step[]).map((s, i) => (
                        <div
                            key={s}
                            className={`flex-1 h-1 rounded-full transition-all ${(step === "form" && i === 0) ||
                                    (step === "upi" && i <= 1) ||
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
                    {step === "upi" && (
                        <UpiStep
                            plan={plan}
                            intentId={intentId}
                            onSubmit={handlePaymentSubmit}
                            onBack={() => { setStep("form"); setError(null); }}
                            loading={loading}
                            error={error}
                        />
                    )}
                    {step === "done" && (
                        <DoneStep plan={plan} onClose={onClose} />
                    )}
                </div>
            </div>
        </div>
    );
}
