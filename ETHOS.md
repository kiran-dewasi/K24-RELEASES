# K24 — Ethos
# What we will never compromise on.
# Every agent reads this. Every product decision is measured against this.
# When in doubt — come back here.

***

## Principle 1: The Data Is Everything

A wholesaler's receivables, cash position, and stock are not app data.
They are his livelihood. His business runs on these numbers being exact.

A wrong receivable means he doesn't chase the right customer.
A wrong inventory count means he over-orders or runs out.
A wrong GST entry means a legal problem — not a bug ticket.

**What this means for builders:**
- Financial calculations surface errors. They never swallow them silently.
- "Works for most cases" is not acceptable. It must work for all cases.
- Any doubt about a financial figure → stop, investigate, fix. Never approximate.
- The shadow DB (k24_shadow.db) must mirror Tally exactly. Drift is a data integrity failure.
- Dashboard data that is wrong is worse than no dashboard.
  Wrong numbers create false confidence. Fix before any user sees them.

> "Our users make business decisions based on what K24 shows them.
>  If the number is wrong, the decision is wrong. That is on us."

***

## Principle 2: The User Never Has to Think About Tally

K24's entire value is that the user's mental model is:
WhatsApp → done. App → done. Tally just works in the background.

The moment a user opens Tally to fix something K24 should have handled,
we have broken our core promise.

**What this means for builders:**
- Every write operation to Tally must be complete — party, item, GST, extra expenses — all of it.
  Partial writes (current desktop GST bug) are a broken promise, not an acceptable beta state.
- When a new party is auto-created from OCR, everything Tally needs must be created too.
  Not just the party name. The GST ledger. All required fields. Everything.
- PDF and Excel exports must be ready for a real business meeting — not rough drafts.
- Kittu answers must be direct, complete, and formally worded.

> "If a wholesaler has to open Tally even once because of K24,
>  we haven't built what we said we were building."

***

## Principle 3: Speed Is Respect

A wholesaler is managing deliveries, payments, staff, and suppliers simultaneously.
Every second K24 wastes is a second taken from his actual business.

**Target benchmarks:**
- Photo → Bill: under 15 seconds end-to-end. Under 10 is the goal.
- WhatsApp pull queries: under 5 seconds. Under 3 is the goal.
- Dashboard load with real data: under 2 seconds.
- Fallback model switches (Flash → Pro): invisible to the user.

> "Every loading spinner is a message: we didn't think hard enough."

***

## Principle 4: Trust Is Earned With Accuracy, Lost With Errors

A wholesaler is trusting K24 with his entire business data.
His Tally. His customers. His receivables. His stock.
That is an enormous ask. He extends that trust once.

**What this means in practice:**
- The .exe launches to a close circle first — not out of caution, but to earn trust correctly.
- Every known bug is fixed before it reaches a paying user.
  Known bugs in production are broken trust waiting to happen.
- Kittu never invents an answer. If it doesn't know, it says so clearly.
- Auth is sacred. One tenant's data never reaches another. Always.

> "We are not building software. We are asking someone to trust us with their business."

***

## Principle 5: Global Scale Is Built on Local Mastery

The vision is worldwide — every business, every country, full financial OS.
But the path goes through Indian wholesalers.

Indian business reality is specific:
- GST has HSN codes, different rates per product, interstate vs intrastate rules.
- Tally is deeply embedded in Indian SMB accounting — it is not going away.
- WhatsApp is the operating system of Indian business communication.
- Hindi and English switch mid-sentence. Kittu handles both without friction.

We don't simplify Indian complexity to fit a global template.
We master Indian complexity so completely that the global version is built on top of it.

Phase 1: 50 wholesalers in Pune who can't live without K24.
Phase 2: India.
Phase 3: The world.
In that order. At that speed.

> "Win the wholesaler in Pune. Then win the world.
>  Not the other way around."
