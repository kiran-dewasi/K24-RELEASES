"use client";

import { useState } from "react";
import { PLANS, FAQ_ITEMS, UPI_CONFIG, type Plan } from "@/lib/plans-config";
import { Check, ChevronDown, ChevronUp, ArrowRight, Building2, Zap, Phone, ShieldCheck, FileText, Receipt } from "lucide-react";
import SubscribeModal from "@/components/pricing/SubscribeModal";

// ─── Design tokens ────────────────────────────────────────────────────────────
// Background : #F8FAFC (slate-50) / white
// Headings   : #0F172A (slate-900)
// Body text  : #475569 (slate-600)
// Accent     : #1D4ED8 (blue-700) — primary buttons, badge, selected states only
// Cards      : white, border-slate-200, rounded-2xl, shadow-sm
// Pro card   : border-2 border-blue-700, shadow-lg

// ─── Navbar ──────────────────────────────────────────────────────────────────

function PricingNav() {
    return (
        <>
            <style>{`
            /* ─── Rotating halo ring around K logo ─── */
            @keyframes k24-ring {
                from { transform: rotate(0deg); }
                to   { transform: rotate(360deg); }
            }
            .k24-halo-spin {
                animation: k24-ring 3s linear infinite;
            }
        `}</style>

            <nav className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-slate-200">
                <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
                    <a href="/" className="flex items-center gap-2.5">

                        {/* Logo — spinning aurora halo */}
                        <div className="relative" style={{ width: 40, height: 40 }}>

                            {/* Rotating conic-gradient outer ring */}
                            <div
                                className="k24-halo-spin absolute inset-0 rounded-[13px]"
                                style={{
                                    background: "conic-gradient(from 0deg, #1D4ED8, #60A5FA, #000, #1D4ED8, #3B82F6, #000000, #1D4ED8)",
                                    padding: 2,
                                    WebkitMask: "linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)",
                                    WebkitMaskComposite: "xor",
                                    maskComposite: "exclude",
                                }}
                            />

                            {/* K box */}
                            <div
                                className="absolute inset-[2.5px] rounded-[11px] flex items-center justify-center text-white font-bold text-sm"
                                style={{ background: "linear-gradient(135deg, #000 0%, #1D4ED8 100%)" }}
                            >
                                K
                            </div>
                        </div>

                        <span className="text-slate-900 font-bold text-[15px] tracking-tight">K24.ai</span>
                    </a>
                    <div className="hidden md:flex items-center gap-8 text-sm text-slate-500">
                        <a href="#pricing" className="hover:text-slate-900 transition-colors">Plans</a>
                        <a href="#how-credits-work" className="hover:text-slate-900 transition-colors">Credits</a>
                        <a href="#faq" className="hover:text-slate-900 transition-colors">FAQ</a>
                    </div>
                    <a
                        href="/login"
                        className="text-sm font-medium px-4 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 transition-all"
                    >
                        Log in
                    </a>
                </div>
            </nav>
        </>
    );
}

// ─── Hero ─────────────────────────────────────────────────────────────────────

function Hero({ onGetStarted }: { onGetStarted: (plan: Plan) => void }) {
    const proPlan = PLANS.find(p => p.id === "pro")!;

    return (
        <section className="pt-32 pb-20 px-6 bg-white text-center">
            <div className="max-w-3xl mx-auto">
                {/* Badge */}
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-blue-200 bg-blue-50 text-blue-700 text-xs font-semibold mb-8 uppercase tracking-wide">
                    Now in early access
                </div>

                {/* Headline */}
                <h1 className="text-4xl sm:text-5xl md:text-[56px] font-bold text-slate-900 leading-[1.1] tracking-tight mb-6">
                    Let K24 handle your{" "}
                    <span className="text-blue-700">Tally work</span>{" "}
                    automatically.
                </h1>

                {/* Subheadline */}
                <p className="text-lg text-slate-600 max-w-2xl mx-auto mb-6 leading-relaxed">
                    Send a bill on WhatsApp. K24 reads it, creates the voucher in Tally, and
                    keeps your books clean — automatically.
                </p>

                {/* Trust line */}
                <p className="text-sm text-slate-400 mb-10">
                    No setup fees · GST invoice provided · Cancel anytime
                </p>

                {/* CTAs */}
                <div className="flex flex-col sm:flex-row gap-3 justify-center">
                    <button
                        onClick={() => onGetStarted(proPlan)}
                        className="inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl bg-blue-700 text-white font-semibold text-sm hover:bg-blue-800 transition-colors shadow-sm"
                    >
                        Start with Pro — ₹3,239/mo
                        <ArrowRight className="h-4 w-4" />
                    </button>
                    <a
                        href="#pricing"
                        className="inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl border border-slate-300 text-slate-700 font-medium text-sm hover:bg-slate-50 transition-colors"
                    >
                        View all plans
                    </a>
                </div>
            </div>
        </section>
    );
}

// ─── Plan Card ────────────────────────────────────────────────────────────────

function PlanCard({ plan, onSelect }: { plan: Plan; onSelect: (p: Plan) => void }) {
    const isEnterprise = plan.id === "enterprise";

    return (
        <div
            className={`relative flex flex-col rounded-2xl p-8 bg-white transition-all duration-200 ${plan.highlight
                ? "border-2 border-blue-700 shadow-lg"
                : "border border-slate-200 shadow-sm hover:shadow-md"
                }`}
        >
            {/* Most Popular badge */}
            {plan.badge && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <span className="inline-block px-4 py-1.5 rounded-full bg-blue-700 text-white text-xs font-bold uppercase tracking-wide shadow-sm">
                        {plan.badge}
                    </span>
                </div>
            )}

            {/* Plan name + tagline */}
            <div className="mb-5">
                <h3 className="text-lg font-bold text-slate-900 mb-1">{plan.name}</h3>
                <p className="text-sm text-slate-500 leading-snug">{plan.description}</p>
            </div>

            {/* Price block */}
            <div className="mb-5">
                {isEnterprise ? (
                    <div>
                        <span className="text-3xl font-bold text-slate-900">Custom</span>
                        <p className="text-slate-500 text-sm mt-1">{plan.price_annual_display}</p>
                        <p className="text-xs text-slate-400 mt-0.5">Annual contract · + 18% GST</p>
                    </div>
                ) : (
                    <div>
                        {/* Original price struck through + discount badge on same row */}
                        <div className="flex items-center gap-2 mb-1.5">
                            <span className="text-sm text-slate-400 line-through">
                                {plan.price_original_annual_display} / year
                            </span>
                            {plan.discount_badge && (
                                <span className="inline-block px-2 py-0.5 rounded-md bg-green-100 text-green-700 text-[10px] font-bold tracking-wide">
                                    {plan.discount_badge}
                                </span>
                            )}
                        </div>
                        {/* Discounted annual price — primary, large */}
                        <div className="flex items-baseline gap-1.5">
                            <span className="text-4xl font-bold text-slate-900">{plan.price_annual_display}</span>
                            <span className="text-slate-500 text-sm font-medium">/ year</span>
                        </div>
                        {/* GST note */}
                        <p className="text-[11px] text-slate-400 mt-1.5">
                            + 18% GST · GST invoice provided
                        </p>
                    </div>
                )}
            </div>

            {/* Key limits (companies + credits) */}
            <div className="flex gap-3 mb-6">
                <div className="flex-1 bg-slate-50 rounded-xl p-3 text-center border border-slate-100">
                    <Building2 className="h-4 w-4 text-slate-400 mx-auto mb-1" />
                    <p className="text-slate-900 font-bold text-sm">{String(plan.companies)}</p>
                    <p className="text-slate-400 text-[10px]">Companies</p>
                </div>
                <div className="flex-1 bg-slate-50 rounded-xl p-3 text-center border border-slate-100">
                    <Zap className="h-4 w-4 text-slate-400 mx-auto mb-1" />
                    <p className="text-slate-900 font-bold text-sm">{String(plan.credits_per_month)}</p>
                    <p className="text-slate-400 text-[10px]">Credits / mo</p>
                </div>
            </div>

            {/* Feature list */}
            <ul className="space-y-2.5 mb-8 flex-1">
                {plan.features.map(f => (
                    <li key={f} className="flex items-start gap-2.5 text-sm text-slate-600">
                        <Check className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
                        <span>{f}</span>
                    </li>
                ))}
            </ul>

            {/* CTA */}
            <button
                onClick={() => onSelect(plan)}
                className={`w-full py-3 rounded-xl font-semibold text-sm transition-all ${plan.cta_variant === "primary"
                    ? "bg-blue-700 text-white hover:bg-blue-800 shadow-sm"
                    : plan.cta_variant === "outline"
                        ? "border border-slate-300 text-slate-700 hover:bg-slate-50"
                        : "bg-slate-100 text-slate-800 hover:bg-slate-200"
                    }`}
            >
                {plan.cta_label}
            </button>
        </div>
    );
}

// ─── How Credits Work ─────────────────────────────────────────────────────────

function HowCreditsWork() {
    const creditItems = [
        { billable: true, text: "1 bill or invoice page processed = 1 credit" },
        { billable: true, text: "1 voucher posted or updated in Tally = 1 credit" },
        { billable: false, text: "Asking Kittu questions — free, always" },
        { billable: false, text: "Viewing dashboards, reports, and P&L — free, always" },
    ];

    return (
        <section id="how-credits-work" className="py-20 px-6 bg-slate-50 scroll-mt-16">
            <div className="max-w-3xl mx-auto">
                <div className="text-center mb-12">
                    <h2 className="text-3xl font-bold text-slate-900 mb-3">
                        How automation credits work
                    </h2>
                    <p className="text-slate-500 max-w-xl mx-auto">
                        We only use a credit when K24 does real accounting work on your behalf.
                        Reading, querying, and reporting are always free.
                    </p>
                </div>

                <div className="grid sm:grid-cols-2 gap-3 mb-8">
                    {creditItems.map(item => (
                        <div
                            key={item.text}
                            className={`flex items-start gap-3 p-4 rounded-xl border ${item.billable
                                ? "bg-white border-slate-200"
                                : "bg-green-50 border-green-100"
                                }`}
                        >
                            <div className={`mt-0.5 h-5 w-5 rounded-full flex items-center justify-center shrink-0 text-[10px] font-bold ${item.billable
                                ? "bg-blue-100 text-blue-700"
                                : "bg-green-100 text-green-700"
                                }`}>
                                {item.billable ? "1" : "✓"}
                            </div>
                            <p className="text-sm text-slate-700 leading-snug">{item.text}</p>
                        </div>
                    ))}
                </div>

                {/* Worked example */}
                <div className="bg-white border border-slate-200 rounded-2xl p-6">
                    <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-4">
                        Example: A typical SME in one month
                    </p>
                    <div className="space-y-2.5 text-sm">
                        {[
                            ["150 vouchers posted to Tally", "150 credits"],
                            ["200 bill pages scanned and extracted", "200 credits"],
                            ["500 queries to Kittu", "Free"],
                            ["Dashboard and GST report views", "Free"],
                        ].map(([action, cost]) => (
                            <div key={action} className="flex items-center justify-between">
                                <span className="text-slate-600">{action}</span>
                                <span className={cost === "Free"
                                    ? "text-green-600 font-semibold"
                                    : "text-slate-900 font-semibold"
                                }>{cost}</span>
                            </div>
                        ))}
                        <div className="border-t border-slate-100 pt-3 flex items-center justify-between font-semibold">
                            <span className="text-slate-900">Total credits used</span>
                            <span className="text-blue-700">350 credits → fits comfortably in Starter</span>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}

// ─── Trust strip ──────────────────────────────────────────────────────────────

function TrustStrip() {
    const points = [
        { icon: ShieldCheck, text: "Transparent ₹ pricing" },
        { icon: FileText, text: "No hidden charges" },
        { icon: Receipt, text: "GST invoice for every payment" },
    ];
    return (
        <section className="py-10 px-6 bg-white border-y border-slate-100">
            <div className="max-w-3xl mx-auto flex flex-col sm:flex-row items-center justify-center gap-8">
                {points.map(({ icon: Icon, text }) => (
                    <div key={text} className="flex items-center gap-2.5 text-slate-500 text-sm">
                        <Icon className="h-4 w-4 text-blue-600 shrink-0" />
                        {text}
                    </div>
                ))}
            </div>
        </section>
    );
}

// ─── FAQ ──────────────────────────────────────────────────────────────────────

function FAQ() {
    const [open, setOpen] = useState<number | null>(null);

    return (
        <section id="faq" className="py-20 px-6 bg-white scroll-mt-16">
            <div className="max-w-2xl mx-auto">
                <h2 className="text-3xl font-bold text-slate-900 text-center mb-12">
                    Frequently asked questions
                </h2>
                <div className="divide-y divide-slate-100 border border-slate-200 rounded-2xl overflow-hidden">
                    {FAQ_ITEMS.map((item, i) => (
                        <div key={i}>
                            <button
                                onClick={() => setOpen(open === i ? null : i)}
                                className="w-full flex items-center justify-between gap-4 px-6 py-5 text-left bg-white hover:bg-slate-50 transition-colors"
                            >
                                <span className="text-slate-900 font-medium text-sm">{item.q}</span>
                                {open === i
                                    ? <ChevronUp className="h-4 w-4 text-blue-600 shrink-0" />
                                    : <ChevronDown className="h-4 w-4 text-slate-400 shrink-0" />
                                }
                            </button>
                            {open === i && (
                                <div className="px-6 pb-5 text-sm text-slate-500 leading-relaxed bg-slate-50 border-t border-slate-100">
                                    {item.a}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}

// ─── Footer CTA ───────────────────────────────────────────────────────────────

function FooterCTA({ onGetStarted }: { onGetStarted: (plan: Plan) => void }) {
    const proPlan = PLANS.find(p => p.id === "pro")!;

    return (
        <section className="py-20 px-6 bg-slate-50 border-t border-slate-200">
            <div className="max-w-2xl mx-auto text-center">
                <h2 className="text-3xl font-bold text-slate-900 mb-3">
                    Ready to automate your Tally work?
                </h2>
                <p className="text-slate-500 mb-8">
                    Account activated within 4 business hours of payment. GST invoice provided.
                </p>
                <div className="flex flex-col sm:flex-row gap-3 justify-center">
                    <button
                        onClick={() => onGetStarted(proPlan)}
                        className="inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl bg-blue-700 text-white font-semibold text-sm hover:bg-blue-800 transition-colors shadow-sm"
                    >
                        Get Pro Plan <ArrowRight className="h-4 w-4" />
                    </button>
                    <a
                        href={`https://wa.me/${UPI_CONFIG.support_whatsapp.replace(/\D/g, "")}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl border border-slate-300 text-slate-700 font-medium text-sm hover:bg-slate-100 transition-colors"
                    >
                        <Phone className="h-4 w-4" /> Contact sales
                    </a>
                </div>
            </div>
        </section>
    );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PricingPage() {
    const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);

    const handleSelect = (plan: Plan) => {
        if (plan.id === "enterprise") {
            window.open(
                `https://wa.me/${UPI_CONFIG.support_whatsapp.replace(/\D/g, "")}`,
                "_blank"
            );
            return;
        }
        setSelectedPlan(plan);
    };

    return (
        <div className="min-h-screen bg-white">
            <PricingNav />

            {/* Hero */}
            <Hero onGetStarted={handleSelect} />

            {/* Trust strip */}
            <TrustStrip />

            {/* Pricing */}
            <section id="pricing" className="py-20 px-6 bg-slate-50 scroll-mt-16">
                <div className="max-w-6xl mx-auto">
                    <div className="text-center mb-12">
                        <h2 className="text-3xl font-bold text-slate-900 mb-2">
                            Simple, transparent pricing
                        </h2>
                        <p className="text-slate-500 mb-2">
                            No hidden fees. Pay only for what K24 does for you.
                        </p>
                        <p className="text-sm font-medium text-blue-700">
                            All plans are billed annually. Save up to 19% compared to monthly pricing.
                        </p>
                    </div>

                    {/* Plan cards — 3 col desktop, 1 col mobile */}
                    <div className="grid md:grid-cols-3 gap-6 lg:gap-8 items-start">
                        {PLANS.map(plan => (
                            <PlanCard key={plan.id} plan={plan} onSelect={handleSelect} />
                        ))}
                    </div>

                    {/* Sub-trust row */}
                    <div className="mt-10 flex flex-wrap justify-center gap-6 text-xs text-slate-400">
                        {[
                            "SSL encrypted",
                            "All prices exclusive of 18% GST",
                            "GST invoice on every payment",
                            "WhatsApp support",
                            "4-hour activation",
                        ].map(t => (
                            <span key={t} className="flex items-center gap-1">
                                <Check className="h-3 w-3 text-blue-500" />
                                {t}
                            </span>
                        ))}
                    </div>
                </div>
            </section>

            <HowCreditsWork />
            <FAQ />
            <FooterCTA onGetStarted={handleSelect} />

            {/* Footer */}
            <footer className="border-t border-slate-200 py-8 px-6 bg-white text-center text-slate-400 text-sm">
                <p>© {new Date().getFullYear()} K24 Technologies. All rights reserved.</p>
                <p className="mt-1 text-xs">Built for Indian SMEs and CA firms.</p>
            </footer>

            {/* Subscribe modal */}
            {selectedPlan && (
                <SubscribeModal
                    plan={selectedPlan}
                    onClose={() => setSelectedPlan(null)}
                />
            )}
        </div>
    );
}
