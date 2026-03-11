/**
 * K24 Plans Configuration — Single Source of Truth
 *
 * BILLING MODEL: Annual only. No monthly option.
 * PRICING: All prices shown are exclusive of GST (18%).
 *
 * Used by: /pricing page, subscription form, admin UI, backend price validation.
 * Update here only — all UI reflects automatically.
 */

export type PlanId = "starter" | "pro" | "enterprise";

export interface Plan {
    id: PlanId;
    name: string;
    description: string;
    // Pricing (all ex-GST)
    price_monthly_equiv: number;    // rupees — shown large on card (annual ÷ 12)
    price_monthly_display: string;    // e.g. "₹1,052"
    price_original_annual_rupees: number;    // full price before discount (0 = not shown)
    price_original_annual_display: string;    // e.g. "₹15,588" (shown struck through)
    price_annual_rupees: number;    // actual discounted charge in ₹ (0 = custom)
    price_annual_paise: number;    // actual charge in paise for payment
    price_annual_display: string;    // e.g. "₹12,627"
    billing_period: string;    // "billed annually"
    discount_badge?: string;    // "19% off"
    gst_rate: number;    // 0.18 — always shown separately
    // Plan limits
    companies: number | string;
    credits_per_month: number | string;
    // Display
    badge?: string;    // "Most Popular"
    cta_label: string;
    cta_variant: "primary" | "outline" | "ghost";
    highlight: boolean;
    features: string[];
    enforcement_mode: "HARD_CAP" | "SOFT_CAP" | "NO_CAP_LOG_ONLY";
}

export const PLANS: Plan[] = [
    {
        id: "starter",
        name: "Starter",
        description: "For small shops and single-entity businesses getting started with accounting automation.",
        // Pricing
        price_monthly_equiv: 1052,
        price_monthly_display: "₹1,052",
        price_original_annual_rupees: 15588,
        price_original_annual_display: "₹15,588",
        price_annual_rupees: 12627,
        price_annual_paise: 1262700,
        price_annual_display: "₹12,627",
        billing_period: "per year",
        discount_badge: "19% off",
        gst_rate: 0.18,
        // Limits
        companies: 1,
        credits_per_month: 500,
        // Display
        cta_label: "Get Starter",
        cta_variant: "ghost",
        highlight: false,
        enforcement_mode: "HARD_CAP",
        features: [
            "1 Tally company",
            "500 automation credits / month",
            "WhatsApp bill scanning",
            "Kittu AI chat — unlimited queries",
            "Standard email support",
        ],
    },
    {
        id: "pro",
        name: "Pro",
        description: "For serious SMEs and small CA firms managing 2–3 companies and high voucher volumes.",
        // Pricing
        price_monthly_equiv: 3239,
        price_monthly_display: "₹3,239",
        price_original_annual_rupees: 47988,
        price_original_annual_display: "₹47,988",
        price_annual_rupees: 38870,
        price_annual_paise: 3887000,
        price_annual_display: "₹38,870",
        billing_period: "per year",
        discount_badge: "19% off",
        gst_rate: 0.18,
        // Limits
        companies: 3,
        credits_per_month: 2500,
        // Display
        badge: "Most Popular",
        cta_label: "Get Pro",
        cta_variant: "primary",
        highlight: true,
        enforcement_mode: "SOFT_CAP",
        features: [
            "Up to 3 Tally companies",
            "2,500 automation credits / month",
            "Priority WhatsApp flows",
            "Faster Tally sync",
            "Bulk document processing",
            "Priority WhatsApp + email support",
        ],
    },
    {
        id: "enterprise",
        name: "Enterprise",
        description: "For CA firms and multi-entity businesses with high volume, custom workflows, and SLA requirements.",
        // Pricing
        price_monthly_equiv: 0,
        price_monthly_display: "Custom",
        price_original_annual_rupees: 0,
        price_original_annual_display: "",
        price_annual_rupees: 0,
        price_annual_paise: 0,
        price_annual_display: "starting ₹10,000+ / month",
        billing_period: "annual contract",
        gst_rate: 0.18,
        // Limits
        companies: "10+",
        credits_per_month: "10,000+",
        // Display
        cta_label: "Talk to sales",
        cta_variant: "outline",
        highlight: false,
        enforcement_mode: "NO_CAP_LOG_ONLY",
        features: [
            "10+ Tally companies",
            "10,000+ credits / month (or custom)",
            "Custom workflows and SLA",
            "Dedicated onboarding support",
            "Dedicated account manager",
            "Custom billing and contracts",
        ],
    },
];

export const PLAN_MAP: Record<PlanId, Plan> = Object.fromEntries(
    PLANS.map(p => [p.id, p])
) as Record<PlanId, Plan>;

// UPI / Payment Config
export const UPI_CONFIG = {
    upi_id:             "kirankdewasi19@ptyes",
    payee_name:         "Kiran K Dewasi",
    qr_image_url:       "/images/k24-upi-qr.png",
    verification_hours: 4,
    support_whatsapp:   "+917851074499",
    // GST / tax
    gst_sac_code:       "998315",
    gst_rate:           0.18,
};

// Credit examples — used in "How credits work" section
export const CREDIT_EXAMPLES = [
    {
        icon: "📄",
        action: "Bill or invoice page processed",
        detail: "Each page scanned by K24 = 1 credit",
        credit: 1,
        free: false,
    },
    {
        icon: "📊",
        action: "Voucher posted to Tally",
        detail: "Each voucher created or updated = 1 credit",
        credit: 1,
        free: false,
    },
    {
        icon: "💬",
        action: "Asking Kittu questions",
        detail: "Balance lookups, GST queries, reports — unlimited",
        credit: 0,
        free: true,
    },
    {
        icon: "📈",
        action: "Viewing dashboards and reports",
        detail: "Daybook, P&L, inventory, compliance — always free",
        credit: 0,
        free: true,
    },
];

// FAQ — all English, includes billing model + GST entries
export const FAQ_ITEMS = [
    {
        q: "What is an automation credit?",
        a: "A credit represents one unit of real accounting work performed by K24. Posting a voucher to Tally or processing a bill/invoice page each costs 1 credit. Informational actions — like asking Kittu questions, viewing reports, or checking dashboards — are always free and do not consume credits.",
    },
    {
        q: "What happens when I run out of credits?",
        a: "On the Starter plan, new document processing and voucher creation will pause until your next monthly cycle resets. On Pro, we alert you before you hit the limit and recommend an upgrade. Your account is never locked — existing data and reports remain fully accessible.",
    },
    {
        q: "Can I pay monthly instead of annually?",
        a: "We currently offer annual plans only. This keeps pricing simple and gives you the best value — you effectively save 19% compared to a theoretical monthly rate. Annual billing is charged as a single payment upfront.",
    },
    {
        q: "Can I upgrade or switch plans later?",
        a: "Yes, at any time. Contact us via WhatsApp or email and we will adjust your plan immediately. Upgrades take effect within 4 business hours. Credits and limits update as soon as the new plan is activated.",
    },
    {
        q: "Is GST charged on top of the plan price?",
        a: "Yes. All K24 plans attract 18% GST as per Indian tax law (SAC code 998315). All displayed prices are exclusive of GST. A GST invoice is shared after payment confirmation. If you are GST-registered, you can claim full Input Tax Credit (ITC) on this amount.",
    },
    {
        q: "How does UPI payment work?",
        a: "Select your plan, fill in your business details, then pay the annual amount (+18% GST) directly to our UPI ID. Submit your UTR (transaction reference number) after paying. Our team verifies within 4 business hours and sends your account credentials to your registered email and WhatsApp number.",
    },
    {
        q: "Do I need to already use Tally?",
        a: "Yes. K24 works on top of your existing Tally installation. You will need Tally running on a Windows PC or server. K24 connects to it and handles document reading, data entry, and sync — Tally remains the accounting record of truth.",
    },
    {
        q: "Is there a free trial?",
        a: "We currently offer a 7-day trial for select businesses. After signing up, contact us on WhatsApp to request trial access. Enterprise customers receive a demo and guided onboarding session before committing.",
    },
];
