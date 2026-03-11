"use client";

import { useRouter } from "next/navigation";
import { useUser } from "@/contexts/UserContext";

/**
 * TrialBanner
 *
 * - Active trial (> 0 days):  amber slim strip at top of the page
 * - Trial ends today (0 days): amber strip with stronger messaging
 * - Trial expired / subscription_status === "expired": full-page blur overlay (non-dismissible)
 * - subscription_status === "active" (or null): renders nothing
 */
export default function TrialBanner() {
    const { user } = useUser();
    const router = useRouter();

    // Don't render if we have no user or subscription data
    if (!user) return null;

    const { subscription_status, trial_ends_at } = user;

    // Nothing to show for active paid subscribers
    if (!subscription_status || subscription_status === "active") return null;

    // Compute days remaining
    const daysRemaining = trial_ends_at
        ? Math.ceil((new Date(trial_ends_at).getTime() - Date.now()) / 86_400_000)
        : null;

    const isExpired =
        subscription_status === "expired" ||
        (daysRemaining !== null && daysRemaining <= 0);

    // ── Expired overlay ────────────────────────────────────────────────────
    if (isExpired) {
        return (
            <div
                style={{
                    position: "fixed",
                    inset: 0,
                    zIndex: 200,
                    backgroundColor: "rgba(255,255,255,0.92)",
                    backdropFilter: "blur(6px)",
                    WebkitBackdropFilter: "blur(6px)",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "24px",
                    padding: "32px",
                }}
            >
                {/* Icon */}
                <div style={{ fontSize: "56px", lineHeight: 1 }}>🔒</div>

                {/* Copy */}
                <div style={{ textAlign: "center", maxWidth: "480px" }}>
                    <h2
                        style={{
                            margin: 0,
                            fontSize: "22px",
                            fontWeight: 700,
                            color: "#111827",
                            marginBottom: "8px",
                        }}
                    >
                        Your free trial has ended
                    </h2>
                    <p
                        style={{
                            margin: 0,
                            fontSize: "15px",
                            color: "#4B5563",
                            lineHeight: "1.6",
                        }}
                    >
                        Upgrade to a K24 plan to continue using accounting automations,
                        WhatsApp scanning, and Tally sync.
                    </p>
                </div>

                {/* CTA */}
                <button
                    onClick={() => router.push("/pricing")}
                    style={{
                        padding: "12px 32px",
                        backgroundColor: "#1D4ED8",
                        color: "#FFFFFF",
                        border: "none",
                        borderRadius: "10px",
                        fontSize: "15px",
                        fontWeight: 600,
                        cursor: "pointer",
                        boxShadow: "0 4px 14px rgba(29,78,216,0.35)",
                        transition: "background-color 0.15s ease",
                    }}
                    onMouseEnter={e =>
                        ((e.currentTarget as HTMLButtonElement).style.backgroundColor = "#1E40AF")
                    }
                    onMouseLeave={e =>
                        ((e.currentTarget as HTMLButtonElement).style.backgroundColor = "#1D4ED8")
                    }
                >
                    See Plans →
                </button>
            </div>
        );
    }

    // ── Active trial strip ─────────────────────────────────────────────────
    if (subscription_status !== "trial") return null;

    const isLastDay = daysRemaining !== null && daysRemaining === 0;

    const message = isLastDay
        ? "🔔  Your trial ends today. Upgrade now to keep access."
        : `⏳  Your free trial ends in ${daysRemaining} day${daysRemaining === 1 ? "" : "s"}.`;

    return (
        <div
            style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "12px",
                padding: "7px 20px",
                backgroundColor: "#FFFBEB",       // amber-50
                borderBottom: "1px solid #FDE68A", // amber-200
                flexShrink: 0,
                fontSize: "13.5px",
                fontWeight: 500,
                color: "#92400E",                  // amber-800
            }}
        >
            <span>{message}</span>

            <button
                onClick={() => router.push("/pricing")}
                style={{
                    flexShrink: 0,
                    padding: "5px 14px",
                    backgroundColor: "#1D4ED8",
                    color: "#FFFFFF",
                    border: "none",
                    borderRadius: "8px",
                    fontSize: "12.5px",
                    fontWeight: 600,
                    cursor: "pointer",
                    whiteSpace: "nowrap",
                    transition: "background-color 0.15s ease",
                }}
                onMouseEnter={e =>
                    ((e.currentTarget as HTMLButtonElement).style.backgroundColor = "#1E40AF")
                }
                onMouseLeave={e =>
                    ((e.currentTarget as HTMLButtonElement).style.backgroundColor = "#1D4ED8")
                }
            >
                Upgrade Now →
            </button>
        </div>
    );
}
