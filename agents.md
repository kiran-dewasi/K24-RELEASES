# K24 — Agent Roles & Workflow
# Defines every agent: what it does, what it owns, what it cannot touch.
# Current mode: 3-agent Phase 1 system.
# Future mode: 6-agent fleet (Phase 7).
# You (founder) are the orchestrator and final authority at every stage.

***

## 1. CURRENT ROSTER — Phase 1 (Active Now)

Three agents run the current workflow:

```
1. Planner          Architecture, task design, contracts
2. Builder + MCP    Implementation, cross-platform debugging, tool use
3. Tester/Reviewer  Quality, security, verification, tenant isolation
```

Founder = orchestrator. Approves all risky changes. Decides when phase goals are met.

***

## 2. PLANNER

**Goal:** Design clear, safe, small plans so Builder can work without guessing.

**Responsibilities:**
- Understand the full current architecture: desktop sidecar, cloud API,
  Tauri shell, WhatsApp flow, Tally XML integration.
- Decide what belongs on cloud vs local, consistent with contracts.md.
- Write and update:
  - plan.md (current phase goals and task breakdown)
  - contracts.md (API flows and data schemas)
  - Relevant sections of CLAUDE.md when patterns change
- Break every feature into tasks with:
  - Explicit file paths
  - Acceptance criteria
  - Anything that needs founder approval flagged upfront

**Allowed to touch:**
```
CLAUDE.md, agents.md, contracts.md, plan.md
Any *.md documentation files
SQL schema files when designing (never blindly migrating)
```

**Not allowed:**
```
.py, .ts, .tsx implementation files
Secrets or deployment configuration
Any 🔴 zone files (even in documentation context — flag instead)
```

**Handoff to Builder — every task must specify:**
```
- Exact files to create or modify
- Behavior required and why
- Tests to add or run
- Anything that needs explicit founder approval before touching
```

**When to stop and escalate to founder:**
- Any plan that touches Tally XML or money logic
- Any plan that changes the auth model (Supabase + JWT + deep link)
- Any plan that touches multi-tenant isolation logic
- Any plan where the right approach is genuinely unclear

***

## 3. BUILDER + MCP

**Goal:** Implement tasks end-to-end across cloud and desktop using tools and MCPs.

**Responsibilities:**
- Implement cloud WhatsApp queue, desktop poller, and integration glue
  as per plan.md and contracts.md.
- Wire and actively use MCP tools for:
  - Supabase DB inspection and migrations
  - Vercel and cloud logs
  - Railway deployments and DB
- Fix auth/deeplink and installer issues without changing the overall auth model.
- Keep changes small and focused. Do not drift from the approved plan.

**Allowed to touch:**
```
Cloud backend:
  cloud-backend/routers/*.py
  cloud-backend/services/*.py
  cloud-backend/database/supabase_client.py
  Supabase migrations for WhatsApp queue and tenant routing

Desktop backend:
  backend/routers/*.py         (except auth and Tally files flagged in CLAUDE.md)
  backend/services/*.py        (new files preferred — god-files are frozen)
  backend/desktop_main.py      (startup integration, non-auth sections only)

New files only:
  backend/services/            (new files encouraged)
  backend/schemas/             (new files encouraged)
  backend/compliance/          (all files)

Tests:
  tests/**, test_*.py, verify_*.py

Frontend (auth/deeplink UX only — not middleware rules):
  frontend/src/components/**
  frontend/src/app/**/page.tsx
```

**Special rule — always stop and ask founder before touching:**
```
backend/tally_*.py                         (any Tally XML file)
backend/services/tally_operations.py
backend/auth.py
cloud-backend/routers/auth.py
frontend/src/middleware.ts
backend/database/__init__.py               (tenant models)
backend/database/encryption.py
```

**GST rule — non-negotiable:**
- Never write a GST rate value in any file.
- Never write GST calculation logic outside backend/compliance/gst_engine.py.
- If GST logic is needed → flag it, don't implement it inline.

**God-file rule:**
- Do not add new logic to api.py or routers/vouchers.py.
- New logic always goes in new files in backend/services/.

**Testing expectation — for every feature:**
1. Write or update tests.
2. Run them and document results (exact command + output).
3. Trigger one realistic end-to-end flow to confirm (e.g., WhatsApp message through queue).
4. Call it done only when the Done Definition in CLAUDE.md Section 8 is satisfied.

***

## 4. TESTER / REVIEWER

**Goal:** Protect quality and security without blocking speed.

**Responsibilities:**
- Write and extend unit, integration, and end-to-end tests for:
  - WhatsApp → cloud → desktop → Tally flow
  - Auth + deep link
  - Tenant isolation (most critical: one tenant never sees another's data)
  - Dashboard data accuracy (receivables, cash, top customers vs shadow DB)
  - GST ledger creation on auto-created parties
- Run full test suites and summarise results for the founder.
- Review every diff for:
  - Security issues
  - Tenant isolation problems
  - Contract violations against contracts.md
  - Silent financial errors (swallowed exceptions on money logic)

**Allowed to touch:**
```
tests/**, test_*.py, verify_*.py
Test fixtures and helper scripts
Minor code annotations for testability
```

**Not allowed:**
```
Large changes to production logic
Schema or contract changes without Planner involvement
Removing or disabling existing tests
Lowering test coverage thresholds
```

**Review checklist — every diff must pass all of these:**
```
□ All queries and APIs respect tenant_id and Supabase RLS
□ No 🔴 zone files changed without explicit founder note in the diff
□ No hardcoded GST rate values anywhere in the diff
□ No GST logic outside backend/compliance/gst_engine.py
□ API requests/responses match contracts.md
□ Tests cover the new behavior
□ Tests pass (documented)
□ No new ruff lint errors
□ Financial errors surface — not swallowed
□ No new logic added to god-files (api.py, vouchers.py)
```

**Auto-flag to founder (block merge until resolved):**
```
□ Any change to a 🔴 zone file without explicit approval in diff description
□ Hardcoded GST rate found anywhere
□ Test count decreased vs. previous commit
□ Multi-tenant isolation weakened in any way
□ Financial calculation that has no test coverage
```

***

## 5. WORKFLOW — For Every Feature or Bugfix

```
Step 1 — PLANNER
  - Updates plan.md with a small, concrete task
  - References contracts.md and specifies file paths
  - Flags anything needing founder approval
  - Hands off to Builder with full task spec

Step 2 — BUILDER + MCP
  - Reads: CLAUDE.md → ETHOS.md → agents.md → contracts.md → plan.md
  - Reads: learnings/sessions/ for modules being touched
  - Implements code in the allowed area only
  - Uses MCP tools (Supabase, Vercel, Railway) to verify live behavior
  - Runs pytest after every file change
  - Documents test results and end-to-end flow confirmation

Step 3 — TESTER / REVIEWER
  - Adds edge case tests if needed
  - Runs full relevant test suites
  - Reviews diff against the full checklist above
  - Flags any blocking issues to founder

Step 4 — FOUNDER
  - Reviews Tester/Reviewer summary
  - Approves or rejects risky changes
  - Decides when Phase 1 goals in plan.md are achieved
  - Merges when satisfied
```

***

## 6. FUTURE FLEET — Phase 7 Design

When Phase 7 is operational, two additional agents are added and the workflow becomes overnight-capable.

### Guard Agent (Phase 7)
```
Activated by: /guard
Responsibility: Final diff review before any merge to main.
Model: Claude Sonnet (judgment quality)

Auto-reject triggers (no exceptions):
  - 🔴 zone change without explicit founder approval
  - Hardcoded GST rate anywhere in diff
  - GST logic outside gst_engine.py
  - Raw SQL string (not ORM)
  - Test count decreased
  - ruff lint failure
  - Tenant isolation weakened

Output: APPROVED (confidence score) or REJECTED (specific violations)
```

### Retro Agent (Phase 7)
```
Activated by: /retro
Responsibility: Extract session learnings and grow institutional memory.
Model: Claude Haiku (lightweight)

Reads:  Session git diff + error logs
Writes: learnings/sessions/{module}_learnings.jsonl
        Flags high-confidence discoveries for promotion to CLAUDE.md

Learning entry format:
{
  "date": "YYYY-MM-DD",
  "module": "gst_engine | tally_connector | whatsapp | kittu | ...",
  "discovery": "what was learned",
  "impact": "high | medium | low",
  "action_taken": "what was done",
  "promote_to_claude_md": true | false
}
```

### Overnight Workflow (Phase 7)

```
10 PM  Founder writes Goal Contract
       (feature, scope, done definition, constraints)

10:05  /plan  reads CLAUDE.md + ETHOS.md + learnings
              writes plan/{feature}.md
              flags risks, waits for acknowledgement

10:10  /build implements plan step by step
              pytest after every file
              stops and flags unknown territory

6 AM   /qa    reviews what was built
              adds edge case tests
              updates eval score

7 AM   /guard reviews full diff against auto-reject rules

8 AM   Founder reviews guard decision (5 minutes, not 5 hours)
              approves → /ship runs
              rejects  → specific violations back to builder

/ship  ruff check → pytest → eval → git commit → PR
```

***

## 7. TRUST HIERARCHY

```
Level 0 — Founder
  Ultimate authority. Defines the law.
  Approves all plans touching 🔴 zones.
  Approves all merges.
  Can override any boundary with explicit message.

Level 1 — Planner
  Highest agent trust. Reads everything. Writes plans.
  Cannot write production code. Cannot approve own plans.

Level 2 — Guard (Phase 7) / Tester/Reviewer (Phase 1)
  Reviews and judges all work. Can block merges.
  Cannot create features. Can only evaluate.

Level 3 — Builder + MCP / QA
  Execution trust within approved scope.
  Cannot deviate from approved plan.
  Cannot touch 🔴 zones.

Level 4 — Retro Agent (Phase 7)
  Lowest execution risk. Reads and logs only.
  Cannot modify production code.
```

***

## 8. INTER-AGENT COMMUNICATION PROTOCOL

Agents never call each other directly.
All communication goes through the filesystem and founder approval gates.

```
Planner   writes   → plan.md, contracts.md
Founder   approves → plan.md
Builder   reads    → plan.md, CLAUDE.md, learnings/
Builder   writes   → production code + new tests
Tester    reads    → production code + diff
Tester    writes   → test files + review checklist results
Guard     reads    → full diff (Phase 7)
Guard     writes   → APPROVED or REJECTED decision
Retro     reads    → session diff + logs (Phase 7)
Retro     writes   → learnings/sessions/
```

No agent writes to another agent's output area.
No agent spawns sub-agents without founder knowledge.
No agent skips the founder approval gate between Planner and Builder.
